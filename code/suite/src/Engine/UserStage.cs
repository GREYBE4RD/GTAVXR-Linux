using System;
using System.IO;
using System.Linq;
using System.Xml;
using System.Collections.Generic;

namespace GtavxrSuite {
    public static class UserTree {
        // Only these files participate in the public release's Story Mode save exchange.
        internal static bool IsStoryData(string relative){
            if(relative.Equals("settings.xml",StringComparison.OrdinalIgnoreCase))return true;
            string[] parts=relative.Split('/');
            bool account=parts.Length==3&&parts[0].Equals("Profiles",StringComparison.OrdinalIgnoreCase);
            bool offline=parts.Length==2&&parts[0].Equals("Default",StringComparison.OrdinalIgnoreCase);
            if(!account&&!offline)return false;
            string name=parts[parts.Length-1];
            if(name.EndsWith(".bak",StringComparison.OrdinalIgnoreCase))name=name.Substring(0,name.Length-4);
            return SaveInfo.IsStorySlot(name)||name.Equals("MISREP0000",StringComparison.OrdinalIgnoreCase)||new[]{"cfg.dat","pc_settings.bin","cloudsavedata.dat","user.xml"}
                .Contains(name,StringComparer.OrdinalIgnoreCase);
        }

        public static List<SaveFileRef> Snapshot(string dir){return Snapshot(dir,false);}

        internal static List<SaveFileRef> Snapshot(string dir,bool storyOnly){
            var list=new List<SaveFileRef>();
            if(!Directory.Exists(dir))return list;
            SafeFs.NoLinks(dir);
            foreach(string f in Files(dir,storyOnly).OrderBy(x=>x,StringComparer.OrdinalIgnoreCase)){
                string rel=Relative(dir,f);
                if(storyOnly&&!IsStoryData(rel))continue;
                SafeFs.NoLinks(f);
                list.Add(new SaveFileRef{relative=SafeFs.Relative(rel),sha256=SafeFs.Hash(f),bytes=new FileInfo(f).Length});
            }
            return list;
        }
        static string Relative(string root,string file){
            return file.Substring(root.TrimEnd('\\').Length+1).Replace('\\','/');
        }

        static IEnumerable<string> Files(string root,bool storyOnly){
            if(!storyOnly)return Directory.GetFiles(root,"*",SearchOption.AllDirectories);
            var files=new List<string>{Path.Combine(root,"settings.xml")};
            string offline=SafeFs.Under(root,"Default");
            string profiles=SafeFs.Under(root,"Profiles");
            if(Directory.Exists(offline))files.AddRange(Directory.GetFiles(offline));
            if(Directory.Exists(profiles)){
                foreach(string account in Directory.GetDirectories(profiles)){
                    SafeFs.NoLinks(account);
                    files.AddRange(Directory.GetFiles(account));
                }
            }
            return files.Where(File.Exists);
        }

        // Copy every listed file from src into an EMPTY or absent dest, verifying each.
        public static void CopyInto(string src,List<SaveFileRef> files,string dest){
            SafeFs.Budget(dest,files.Sum(f=>f.bytes));
            Directory.CreateDirectory(dest);
            foreach(var f in files){
                string target=SafeFs.Under(dest,f.relative);
                if(File.Exists(target)){File.SetAttributes(target,FileAttributes.Normal);File.Delete(target);}
                SafeFs.CopyNew(SafeFs.Under(src,f.relative),target,f.sha256,f.bytes);
            }
        }
        // Make dest contain exactly the listed files from src (extra files removed, then empty folders).
        public static void Mirror(string src,List<SaveFileRef> files,string dest){
            Mirror(src,files,dest,false);
        }

        internal static void Mirror(string src,List<SaveFileRef> files,string dest,bool storyOnly){
            Directory.CreateDirectory(dest);SafeFs.NoLinks(dest);
            var changes=files.Where(f=>{
                string target=SafeFs.Under(dest,f.relative);
                return !File.Exists(target)||new FileInfo(target).Length!=f.bytes||
                       !String.Equals(SafeFs.Hash(target),f.sha256,StringComparison.OrdinalIgnoreCase);
            }).ToList();
            if(changes.Count!=0)SafeFs.Budget(dest,changes.Sum(f=>f.bytes));
            var keep=new HashSet<string>(files.Select(f=>f.relative),StringComparer.OrdinalIgnoreCase);
            foreach(string f in Files(dest,storyOnly)){
                string rel=Relative(dest,f);
                if((!storyOnly||IsStoryData(rel))&&!keep.Contains(rel))SafeFs.DeleteName(SafeFs.Under(dest,rel));
            }
            foreach(var f in changes)
                SafeFs.ReplaceFrom(SafeFs.Under(src,f.relative),SafeFs.Under(dest,f.relative),f.sha256,f.bytes,0);
            if(storyOnly)return;
            foreach(string d in Directory.GetDirectories(dest,"*",SearchOption.AllDirectories).OrderByDescending(x=>x.Length))
                if(!Directory.EnumerateFileSystemEntries(d).Any())Directory.Delete(d);
        }
        public static void Verify(string dir,List<SaveFileRef> files){
            foreach(var f in files)SafeFs.AssertFile(SafeFs.Under(dir,f.relative),f.sha256,f.bytes);
        }
    }

    // GTAVXR plays windowed 1920x1080 with Stereo=0 on the monitor; the headset gets its own eyes.
    // The standard display conversion changes four fields. The embedded release also guards its shader set.
    public static class Display {
        internal static Dictionary<string,string> DiagnosticSettings(string path){
            var result=new Dictionary<string,string>();
            if(!File.Exists(path))return result;
            var settings=new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null,MaxCharactersInDocument=1024*1024};
            var doc=new XmlDocument{XmlResolver=null};
            SafeFs.NoLinks(path);
            using(var stream=File.OpenRead(path))
            using(var reader=XmlReader.Create(stream,settings))doc.Load(reader);
            foreach(string group in new[]{"graphics","video"}){
                foreach(XmlElement element in doc.SelectNodes("/Settings/"+group+"/*")){
                    string value=element.GetAttribute("value");
                    if(value.Length<=40 && System.Text.RegularExpressions.Regex.IsMatch(value,@"\A(?:true|false|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\z"))
                        result[group+"."+element.Name]=value;
                }
            }
            return result;
        }

        public static string Convert(string xml){
            bool adjusted;
            return Convert(xml,false,out adjusted);
        }

        internal static string Convert(string xml,bool requireStandardShaders,out bool adjusted){
            var settings=new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null};
            var doc=new XmlDocument{PreserveWhitespace=true,XmlResolver=null};
            using(var r=XmlReader.Create(new StringReader(xml),settings))doc.Load(r);
            var wanted=new Dictionary<string,int>{{"ScreenWidth",1920},{"ScreenHeight",1080},{"Windowed",1},{"Stereo",0}};
            foreach(var w in wanted){
                var nodes=doc.SelectNodes("/Settings/video/"+w.Key);
                if(nodes==null||nodes.Count!=1||!(nodes[0] is XmlElement)||!((XmlElement)nodes[0]).HasAttribute("value"))throw new InvalidDataException("Missing/duplicate display field: "+w.Key);
                var e=(XmlElement)nodes[0];int value;
                if(!Int32.TryParse(e.GetAttribute("value"),out value))throw new InvalidDataException("Invalid display value: "+w.Key);
                if(((w.Key=="ScreenWidth"||w.Key=="ScreenHeight")&&value<=0)||(w.Key=="Windowed"&&(value<0||value>2))||(w.Key=="Stereo"&&(value<0||value>1)))throw new InvalidDataException("Unsupported display value: "+w.Key);
                e.SetAttribute("value",w.Value.ToString(System.Globalization.CultureInfo.InvariantCulture));
            }
            adjusted=false;
            if(requireStandardShaders){
                var nodes=doc.SelectNodes("/Settings/graphics/ShaderQuality");
                var element=nodes.Count==1?nodes[0] as XmlElement:null;
                int quality;
                // Quality 0 selects win32_40_lq, which the embedded release does not supply.
                if(element!=null&&Int32.TryParse(element.GetAttribute("value"),out quality)&&quality==0){
                    element.SetAttribute("value","1");
                    adjusted=true;
                }
            }
            return doc.OuterXml;
        }
    }
}
