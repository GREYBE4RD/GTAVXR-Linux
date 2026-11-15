using System;
using System.IO;
using System.Linq;
using System.Diagnostics;
using System.Threading;

namespace GtavxrSuite {
    // The Suite installs and updates itself: one EXE in %LOCALAPPDATA%\Programs\GTAVXR, shortcuts in Start and on the Desktop.
    // The developer-only channel is separate from public release discovery.
    public static class SelfInstall {
        const string Public100Hash="ABB7544718CC7D33CDA7891AF6B81654615D992D924CB55D935B5D5613132613";
        public static string InstallDir(){return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","GTAVXR");}
        public static string InstalledExe(){return Path.Combine(InstallDir(),"GTAVXR.exe");}
        public static bool RunningInstalled(){return String.Equals(Path.GetFullPath(Program.SelfPath),Path.GetFullPath(InstalledExe()),StringComparison.OrdinalIgnoreCase);}
        public static bool Installed(){return File.Exists(InstalledExe());}

        internal static bool IsPublic100(string path){
            SafeFs.NoLinks(path);
            var file=new FileInfo(path);
            return file.Exists&&file.Length==25437184&&SafeFs.Hash(path)==Public100Hash;
        }

        internal static void RefreshInstalledLauncher(){
            if(!RunningInstalled()&&IsPublic100(InstalledExe()))ReplacePublic100(InstalledExe());
        }

        internal static void ReplacePublic100(string path){
            path=Path.GetFullPath(path);
            if(!IsPublic100(path))throw new InvalidDataException("The selected file is not the original GTAVXR 1.0.0 launcher.");
            var current=new FileInfo(Program.SelfPath);
            string hash=SafeFs.Hash(current.FullName);
            string temporary=Path.Combine(Path.GetDirectoryName(path),".gtavxr-update-"+Ids.New()+".tmp");
            try{
                SafeFs.CopyNew(current.FullName,temporary,hash,current.Length);
                if(!IsPublic100(path))throw new IOException("The selected launcher changed: "+path);
                File.Replace(temporary,path,null);
                SafeFs.AssertFile(path,hash,current.Length);
            }finally{
                if(File.Exists(temporary))SafeFs.DeleteName(temporary);
            }
        }

        internal static void RemovePublic100(string path){
            if(!IsPublic100(path))throw new InvalidDataException("The selected file is not the original GTAVXR 1.0.0 launcher.");
            SafeFs.DeleteName(path);
            if(File.Exists(path))throw new IOException("Could not remove: "+path);
        }

        internal static void RemoveOwnShortcuts(string installed,System.Collections.Generic.IEnumerable<string> targets){
            foreach(string directory in targets.Where(p=>!String.IsNullOrEmpty(p)).Distinct(StringComparer.OrdinalIgnoreCase)){
                string path=SafeFs.Under(directory,"GTAVXR.lnk");
                if(!File.Exists(path))continue;
                var type=Type.GetTypeFromProgID("WScript.Shell");
                if(type==null)throw new IOException("Could not verify shortcut: "+path);
                dynamic shell=Activator.CreateInstance(type);
                dynamic link=null;
                try{
                    link=shell.CreateShortcut(path);
                    string destination=link.TargetPath;
                    if(!String.Equals(destination,installed,StringComparison.OrdinalIgnoreCase))continue;
                    SafeFs.DeleteName(path);
                    if(File.Exists(path))throw new IOException("Could not remove shortcut: "+path);
                }finally{
                    if(link!=null)System.Runtime.InteropServices.Marshal.FinalReleaseComObject(link);
                    System.Runtime.InteropServices.Marshal.FinalReleaseComObject(shell);
                }
            }
        }

        // Copy this EXE into place and create the shortcuts. Returns the installed path.
        public static string Install(string targetDir,string startMenu,string desktop){
            Directory.CreateDirectory(targetDir);
            string dest=Path.Combine(targetDir,"GTAVXR.exe");
            string tmp=dest+"."+Ids.New()+".tmp";File.Copy(Program.SelfPath,tmp);
            if(SafeFs.Hash(tmp)!=SafeFs.Hash(Program.SelfPath)){File.Delete(tmp);throw new IOException("Copy check failed");}
            if(File.Exists(dest))File.Replace(tmp,dest,null);else File.Move(tmp,dest);
            if(startMenu!=null)Shortcut(Path.Combine(startMenu,"GTAVXR.lnk"),dest);
            if(desktop!=null)Shortcut(Path.Combine(desktop,"GTAVXR.lnk"),dest);
            return dest;
        }
        public static string Install(){
            return Install(InstallDir(),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs)),Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory));
        }
        static void Shortcut(string lnk,string target){
            var t=Type.GetTypeFromProgID("WScript.Shell");if(t==null)return;
            dynamic shell=Activator.CreateInstance(t);
            try{dynamic s=shell.CreateShortcut(lnk);s.TargetPath=target;s.WorkingDirectory=Path.GetDirectoryName(target);s.Description="GTAVXR";s.IconLocation=target+",0";s.Save();}
            finally{System.Runtime.InteropServices.Marshal.FinalReleaseComObject(shell);}
        }

        // ---- updates from the local channel ----
        public class ChannelBuild { public string schema {get;set;} public string version {get;set;} public string sha256 {get;set;} public long bytes {get;set;} public string notes {get;set;} }
        public static string ChannelDir(Env env){return env.DevRepo==null?null:Path.Combine(env.DevRepo,"local-cache","suite","channel");}
        public static ChannelBuild Available(Env env){
            string d=ChannelDir(env);if(d==null)return null;string f=Path.Combine(d,"latest.json");if(!File.Exists(f))return null;
            var b=Json.Read<ChannelBuild>(f);
            if(b.schema!="gtavxr-suite2-channel-v1"||!SafeFs.IsHash(b.sha256))return null;
            string exe=Path.Combine(d,b.sha256.ToUpperInvariant()+".exe");if(!File.Exists(exe))return null;
            if(String.Equals(SafeFs.Hash(Program.SelfPath),b.sha256,StringComparison.OrdinalIgnoreCase))return null;
            if(Compare(b.version,SuiteApp.Version)<=0)return null;
            return b;
        }
        public static int Compare(string a,string b){
            var x=(a??"0").Split('.','-').Select(p=>{int n;return Int32.TryParse(p,out n)?n:0;}).ToArray();
            var y=(b??"0").Split('.','-').Select(p=>{int n;return Int32.TryParse(p,out n)?n:0;}).ToArray();
            for(int i=0;i<Math.Max(x.Length,y.Length);i++){int u=i<x.Length?x[i]:0,v=i<y.Length?y[i]:0;if(u!=v)return u.CompareTo(v);}
            return 0;
        }
        // Start the new EXE as a helper that waits for this process to exit, replaces this EXE and restarts it.
        public static void ApplyUpdate(Env env,ChannelBuild b,bool restart){
            string src=Path.Combine(ChannelDir(env),b.sha256.ToUpperInvariant()+".exe");
            SafeFs.AssertFile(src,b.sha256,b.bytes);
            string helper=Path.Combine(Path.GetTempPath(),"gtavxr-update-"+Ids.New()+".exe");File.Copy(src,helper);
            using(var self=Process.GetCurrentProcess())
                Process.Start(new ProcessStartInfo(helper,ProcessText.Join(new[]{"--finish-update",Program.SelfPath,self.Id.ToString(),restart?"restart":"no-restart"})){UseShellExecute=false,CreateNoWindow=true});
        }
        // Runs inside the helper copy. Never touches anything but the target EXE.
        public static int FinishUpdate(string target,int pid,bool restart){
            try{using(var p=Process.GetProcessById(pid))p.WaitForExit(60000);}catch(ArgumentException){}
            string self=Program.SelfPath;string tmp=target+"."+Ids.New()+".tmp";
            for(int i=0;i<50;i++){
                try{File.Copy(self,tmp,true);if(File.Exists(target))File.Replace(tmp,target,null);else File.Move(tmp,target);break;}
                catch(IOException){Thread.Sleep(200);if(i==49)throw;}
                catch(UnauthorizedAccessException){Thread.Sleep(200);if(i==49)throw;}
            }
            if(restart)Process.Start(new ProcessStartInfo(target){UseShellExecute=true});
            return 0;
        }
        // Development pipeline: publish a built EXE to the channel (called from tools/publish_channel.ps1 via --publish-channel).
        public static object Publish(string repo,string exe,string version,string notes){
            string d=Path.Combine(repo,"local-cache","suite","channel");Directory.CreateDirectory(d);
            string sha=SafeFs.Hash(exe);long bytes=new FileInfo(exe).Length;string dest=Path.Combine(d,sha+".exe");
            if(!File.Exists(dest))SafeFs.CopyNew(exe,dest,sha,bytes);
            Json.Atomic(Path.Combine(d,"latest.json"),new ChannelBuild{schema="gtavxr-suite2-channel-v1",version=version,sha256=sha,bytes=bytes,notes=notes});
            return new{status="PUBLISHED",version=version,sha256=sha,bytes=bytes};
        }
    }
}
