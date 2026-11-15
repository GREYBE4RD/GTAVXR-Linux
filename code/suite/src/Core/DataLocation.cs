using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace GtavxrSuite {
    internal sealed class DataLocation {
        readonly string fallback, pointer;

        internal DataLocation(string defaultRoot) {
            fallback=SafeFs.Root(defaultRoot);
            pointer=SafeFs.Under(Path.GetDirectoryName(fallback),"suite-location.json");
        }

        internal string Resolve() {
            if(!File.Exists(pointer))return fallback;
            var config=ReadPointer();
            string root=Path.GetFullPath(config.path);
            if(!Directory.Exists(root))throw new IOException("DATA_LOCATION_UNAVAILABLE: "+root);
            root=SafeFs.Root(root);
            if(!File.Exists(SafeFs.Under(root,"settings.json")))throw new IOException("DATA_LOCATION_UNAVAILABLE: "+root);
            return root;
        }

        internal IEnumerable<string> KnownLibraries() {
            if(!File.Exists(pointer))return new[]{fallback};
            var config=ReadPointer();
            return new[]{Resolve(),fallback}.Concat(config.previous??new List<string>()).Distinct(StringComparer.OrdinalIgnoreCase);
        }

        internal void SelectExisting(string directory) {
            string target=SafeFs.Root(directory);
            string problem=PlatformCompatibility.SessionPathProblem(target);
            if(problem!=null)throw new InvalidDataException(problem);
            var settings=Json.Read<SuiteSettings>(SafeFs.Under(target,"settings.json"));
            if(settings==null||settings.schema!="gtavxr-suite2-settings-v1")
                throw new InvalidDataException("Select an existing GTAVXR Suite data folder.");
            LocationRecord previous=null;
            if(File.Exists(pointer)){
                try{previous=ReadPointer();}
                catch(InvalidDataException){
                    string rejected=pointer+".invalid-"+Ids.New();
                    var file=new FileInfo(pointer);
                    SafeFs.CopyNew(pointer,rejected,SafeFs.Hash(pointer),file.Length);
                }
            }
            Directory.CreateDirectory(Path.GetDirectoryName(pointer));
            Json.Atomic(pointer,new LocationRecord{schema="gtavxr-suite-data-location-v1",path=target,
                previous=(previous==null?new[]{fallback}:(previous.previous??new List<string>()).Concat(new[]{previous.path}))
                    .Where(path=>!String.Equals(path,target,StringComparison.OrdinalIgnoreCase)).Distinct(StringComparer.OrdinalIgnoreCase).ToList()});
        }

        internal string Pointer { get { return pointer; } }

        LocationRecord ReadPointer() {
            LocationRecord config;
            try{config=Json.Read<LocationRecord>(pointer);}
            catch(FormatException error){throw new InvalidDataException("DATA_LOCATION_INVALID",error);}
            catch(InvalidDataException error){throw new InvalidDataException("DATA_LOCATION_INVALID",error);}
            catch(ArgumentException error){throw new InvalidDataException("DATA_LOCATION_INVALID",error);}
            catch(InvalidOperationException error){throw new InvalidDataException("DATA_LOCATION_INVALID",error);}
            if(config==null||config.schema!="gtavxr-suite-data-location-v1"||
               !Path.IsPathRooted(config.path)||config.previous!=null&&config.previous.Any(path=>!Path.IsPathRooted(path)))
                throw new InvalidDataException("DATA_LOCATION_INVALID");
            return config;
        }

        static bool Contains(string parent,string child) {
            return String.Equals(parent,child,StringComparison.OrdinalIgnoreCase)||
                   child.StartsWith(parent+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase);
        }

        static bool Overlaps(string first,string second) {
            return Contains(first,second)||Contains(second,first);
        }

        static IEnumerable<FileEntry> Walk(string root,string relative) {
            string dir=relative.Length==0?root:SafeFs.Under(root,relative);
            foreach(string full in Directory.EnumerateFileSystemEntries(dir).OrderBy(path=>path,StringComparer.OrdinalIgnoreCase)){
                string name=Path.GetFileName(full);
                string key=relative.Length==0?name:relative+"/"+name;
                SafeFs.NoLinks(full);
                var attributes=File.GetAttributes(full);
                bool directory=(attributes&FileAttributes.Directory)!=0;
                yield return new FileEntry { relative=key, directory=directory, bytes=directory?0:new FileInfo(full).Length };
                if(directory)
                    foreach(var child in Walk(root,key))yield return child;
            }
        }

        internal static bool SameProfileFiles(string first,string second) {
            var left=Walk(first,"").ToList();
            var right=Walk(second,"").ToList();
            if(left.Count!=right.Count)return false;
            for(int index=0;index<left.Count;index++){
                var a=left[index];var b=right[index];
                if(a.directory!=b.directory||a.bytes!=b.bytes||
                   !String.Equals(a.relative,b.relative,StringComparison.OrdinalIgnoreCase))return false;
            }
            foreach(var entry in left.Where(row=>!row.directory)){
                string a=SafeFs.Under(first,entry.relative),b=SafeFs.Under(second,entry.relative);
                if(!String.Equals(SafeFs.Hash(a),SafeFs.Hash(b),StringComparison.OrdinalIgnoreCase))return false;
            }
            return true;
        }

        internal void CopyAndSelect(Env env,string destination,string setupGame=null) {
            using(var library=GameScope.Acquire(env.DataRoot))
            using(var game=Directory.Exists(env.GameDir)?GameScope.Acquire(env.GameDir):null)
                CopyAndSelectOwned(env,destination,setupGame);
        }

        void CopyAndSelectOwned(Env env,string destination,string setupGame) {
            string source=SafeFs.Root(env.DataRoot);
            string target=SafeFs.Root(destination);
            if(!String.Equals(source,Resolve(),StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("DATA_LOCATION_STALE");
            string issue=PlatformCompatibility.SessionPathProblem(target);
            if(issue!=null)throw new InvalidDataException(issue);
            var drive=new DriveInfo(Path.GetPathRoot(target));
            if(drive.DriveType!=DriveType.Fixed&&drive.DriveType!=DriveType.Removable)
                throw new InvalidDataException("DATA_PATH_NOT_LOCAL");
            string parent=Path.GetDirectoryName(target);
            if(!Directory.Exists(parent))throw new DirectoryNotFoundException(parent);
            if(Overlaps(source,target)||Overlaps(fallback,target)||
               new[]{env.GameDir,setupGame,env.UserDataDir}.Any(path=>!String.IsNullOrEmpty(path)&&Overlaps(SafeFs.Root(path),target)))
                throw new InvalidDataException("DATA_LOCATION_OVERLAP");
            if(File.Exists(target)||Directory.Exists(target))throw new IOException("DATA_LOCATION_EXISTS");
            CheckIdle(env);
            var configured=env.LoadSettings();

            var files=Walk(source,"").ToList();
            SafeFs.Budget(target,files.Sum(row=>row.bytes));
            string stage=SafeFs.Under(parent,".gtavxr-suite-copy-"+Ids.New());
            Directory.CreateDirectory(stage);
            bool renamed=false, committed=false;
            try{
                foreach(var entry in files){
                    string from=SafeFs.Under(source,entry.relative);
                    string to=SafeFs.Under(stage,entry.relative);
                    if(entry.directory)Directory.CreateDirectory(to);
                    else{
                        entry.hash=SafeFs.Hash(from);
                        SafeFs.CopyNew(from,to,entry.hash,entry.bytes);
                        File.SetLastWriteTimeUtc(to,File.GetLastWriteTimeUtc(from));
                    }
                }
                var after=Walk(source,"").ToList();
                if(!files.Select(x=>x.relative).SequenceEqual(after.Select(x=>x.relative),StringComparer.Ordinal))
                    throw new IOException("DATA_LOCATION_CHANGED");
                foreach(var entry in files.Where(x=>!x.directory))
                    SafeFs.AssertFile(SafeFs.Under(source,entry.relative),entry.hash,entry.bytes);
                CheckIdle(env);
                // An explicitly selected DLSS folder below the old library follows the verified copy.
                string settings=SafeFs.Under(stage,"settings.json");
                string originalDlss=configured.dlss_dir;
                if(!String.IsNullOrEmpty(originalDlss)&&Path.IsPathRooted(originalDlss)){
                    string dlss=Path.GetFullPath(originalDlss).TrimEnd(Path.DirectorySeparatorChar);
                    if(Contains(source,dlss))configured.dlss_dir=target+dlss.Substring(source.Length);
                }
                bool keepSetupGame=configured.game_dir==null&&!String.IsNullOrEmpty(setupGame);
                if(keepSetupGame)configured.game_dir=SafeFs.Root(setupGame);
                if(!File.Exists(settings)||configured.dlss_dir!=originalDlss||keepSetupGame)Json.Atomic(settings,configured);
                foreach(var entry in files.Where(x=>!x.directory&&x.relative.StartsWith("blobs/",StringComparison.OrdinalIgnoreCase)))
                    File.SetAttributes(SafeFs.Under(stage,entry.relative),FileAttributes.ReadOnly);
                SafeFs.NoLinks(target);
                Directory.Move(stage,target);
                renamed=true;
                Directory.CreateDirectory(Path.GetDirectoryName(pointer));
                var history=File.Exists(pointer)?ReadPointer().previous:null;
                Json.Atomic(pointer,new LocationRecord { schema="gtavxr-suite-data-location-v1", path=target,
                    previous=(history??new List<string>()).Concat(new[]{source}).Distinct(StringComparer.OrdinalIgnoreCase).ToList() });
                committed=true;
            }finally{
                if(!committed&&!renamed&&Directory.Exists(stage)){
                    try{
                        foreach(var entry in Walk(stage,"").Where(x=>!x.directory))
                            SafeFs.DeleteName(SafeFs.Under(stage,entry.relative));
                        Directory.Delete(SafeFs.Root(stage),true);
                    }catch(IOException){}catch(UnauthorizedAccessException){}
                }
            }
        }

        static void CheckIdle(Env env) {
            var session=new PlaySession(env);
            if(session.GameRunning())throw new InvalidOperationException("GAME_RUNNING");
            if(new GameLayer(env).Pending||session.Unfinished().Count!=0)
                throw new InvalidOperationException("RECOVERY_REQUIRED");
            if(new ReleaseMigration(env).Pending)
                throw new InvalidOperationException("An update is unfinished. Select Update GTAVXR to resume.");
        }

        sealed class FileEntry {
            internal string relative, hash;
            internal bool directory;
            internal long bytes;
        }

        internal sealed class LocationRecord {
            public string schema {get;set;}
            public string path {get;set;}
            public List<string> previous {get;set;}
        }
    }
}
