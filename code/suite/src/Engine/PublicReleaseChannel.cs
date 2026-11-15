using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;
using System.Web.Script.Serialization;

namespace GtavxrSuite {
    internal static class PublicReleaseChannel {
        internal const string Releases="https://github.com/LVL-VR/GTAVXR/releases";
        const string Latest="https://api.github.com/repos/LVL-VR/GTAVXR/releases/latest";

        internal sealed class Asset {
            public string name { get; set; }
            public string state { get; set; }
            public string digest { get; set; }
            public long size { get; set; }
            public string browser_download_url { get; set; }
        }
        sealed class Release {
            public string tag_name { get; set; }
            public bool draft { get; set; }
            public bool prerelease { get; set; }
            public List<Asset> assets { get; set; }
        }
        internal sealed class Update {
            internal Version Version;
            internal string Page;
            internal string Hash;
            internal long Bytes;
        }

        internal static Update Check() {
            var request=(HttpWebRequest)WebRequest.Create(Latest);
            request.AllowAutoRedirect=false;
            request.Timeout=10000;
            request.ReadWriteTimeout=10000;
            request.UserAgent="GTAVXR/"+SuiteApp.Version;
            request.Accept="application/vnd.github+json";
            using(var response=(HttpWebResponse)request.GetResponse())
            using(var source=response.GetResponseStream())
            using(var data=new MemoryStream()){
                if(response.StatusCode!=HttpStatusCode.OK)throw new IOException("GitHub release check failed.");
                var buffer=new byte[8192];
                for(int count;(count=source.Read(buffer,0,buffer.Length))>0;){
                    if(data.Length+count>1024*1024)throw new InvalidDataException("GitHub release metadata is too large.");
                    data.Write(buffer,0,count);
                }
                return Parse(new UTF8Encoding(false,true).GetString(data.ToArray()),new Version(SuiteApp.Version));
            }
        }

        internal static Update Parse(string json,Version current) {
            StrictJson.Validate(json);
            var release=new JavaScriptSerializer{MaxJsonLength=1024*1024,RecursionLimit=48}.Deserialize<Release>(json);
            Version version;
            if(release==null||release.draft||release.prerelease||String.IsNullOrEmpty(release.tag_name)||
               !release.tag_name.StartsWith("v",StringComparison.Ordinal)||
               !Version.TryParse(release.tag_name.Substring(1),out version)||version.Build<0||version.Revision>=0||
               release.tag_name!="v"+version.ToString(3))
                throw new InvalidDataException("GitHub did not return a stable GTAVXR release.");
            if(version<=current)return null;
            var assets=(release.assets??new List<Asset>()).Where(a=>a!=null&&a.name=="GTAVXR.exe").ToList();
            string expected=Releases+"/download/"+release.tag_name+"/GTAVXR.exe";
            if(assets.Count!=1||assets[0].state!="uploaded"||assets[0].browser_download_url!=expected||
               assets[0].size<=0||assets[0].size>512L*1024*1024)
                throw new InvalidDataException("The official GTAVXR.exe asset is unavailable.");
            string digest=assets[0].digest;
            if(digest!=null&&(!digest.StartsWith("sha256:",StringComparison.Ordinal)||!SafeFs.IsHash(digest.Substring(7))))
                throw new InvalidDataException("The release hash is invalid.");
            return new Update{Version=version,Page=Releases+"/tag/"+release.tag_name,
                Hash=digest==null?null:digest.Substring(7).ToUpperInvariant(),Bytes=assets[0].size};
        }

        internal static void VerifyDownload(Update update,string path) {
            if(update.Hash==null)throw new InvalidDataException("GitHub did not provide a hash for this download.");
            SafeFs.AssertFile(path,update.Hash,update.Bytes);
        }
    }
}
