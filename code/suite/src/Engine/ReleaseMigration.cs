using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace GtavxrSuite {
    internal sealed class ReleaseMigration {
        sealed class Journal {
            public string target { get; set; }
            public string bundle { get; set; }
            public string game { get; set; }
            public string selected { get; set; }
            public Dictionary<string,string> profiles { get; set; }
            public List<VersionManifest> retired { get; set; }
        }

        readonly Env env;
        readonly Library library;
        readonly string path;

        internal ReleaseMigration(Env env) {
            this.env=env;
            library=new Library(env);
            path=SafeFs.Under(env.DataRoot,"release-migration.json");
        }

        internal bool Pending { get { return File.Exists(path); } }

        internal static void CheckPublicGamePaths(Env env,GameState state) {
            if(state!=null&&!String.Equals(SafeFs.Root(state.game_dir),SafeFs.Root(env.GameDir),StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("This library still manages another GTA folder: "+state.game_dir+
                    ". Reconnect or locate that installation and uninstall GTAVXR from it first.");
        }

        internal void CheckLibraries(VersionManifest target,string selected,DataLocation location=null) {
            if((!env.ManagedLocation&&location==null)||Pending||Plan(target,selected)==null)return;
            location=location??new DataLocation(Env.DefaultDataRoot());
            foreach(string directory in location.KnownLibraries()){
                if(String.Equals(directory,env.DataRoot,StringComparison.OrdinalIgnoreCase))continue;
                if(!new DriveInfo(Path.GetPathRoot(directory)).IsReady)
                    throw new IOException("Reconnect the previous GTAVXR library drive: "+directory);
                if(!Directory.Exists(directory))continue;
                using(var previous=GameScope.Acquire(directory)){
                    string oldProfiles=SafeFs.Under(directory,"profiles");
                    if(!Directory.Exists(oldProfiles))continue;
                    foreach(string profile in Directory.EnumerateDirectories(oldProfiles)){
                        string id=Path.GetFileName(profile);
                        string oldRecord=SafeFs.Under(profile,"profile.json");
                        if(!File.Exists(oldRecord))continue;
                        var old=Json.Read<Profile>(oldRecord);
                        if(old==null||old.id!=id||old.schema!="gtavxr-suite2-profile-v1")
                            throw new InvalidDataException("Invalid previous profile record: "+oldRecord);
                        if(PublicVersion(old.version)==null)continue;
                        Ids.Check(id);
                        string active=SafeFs.Under(env.DataRoot,"profiles/"+id);
                        if((!Directory.Exists(active)||!DataLocation.SameProfileFiles(profile,active))&&
                            !ContainsImportedStory(profile,old,library.Profile(id)??library.Profile(selected)))
                            throw new IOException("Another Suite library has a different profile or save. Review the original library or import its saves from the Save tab: "+profile);
                    }
                }
            }
        }

        bool ContainsImportedStory(string previous,Profile source,Profile current) {
            if(current==null)return false;
            var candidates=StoryStart.Choices(current).ToList();
            var saves=StoryStart.Choices(source).ToList();
            if(saves.Count==0)return false;
            string destination=library.UserDir(current.id);
            string from=SafeFs.Under(previous,"user");
            foreach(var save in saves){
                string name=Path.GetFileName(save.relative);
                var copied=candidates.FirstOrDefault(file=>file.bytes==save.bytes&&
                    String.Equals(file.sha256,save.sha256,StringComparison.OrdinalIgnoreCase)&&
                    (String.Equals(file.relative,save.relative,StringComparison.OrdinalIgnoreCase)||
                     String.Equals(file.relative,StoryStart.Archive+"import-"+save.sha256+"/"+name,StringComparison.OrdinalIgnoreCase)));
                if(copied==null)return false;
                SafeFs.AssertFile(SafeFs.Under(from,save.relative),save.sha256,save.bytes);
                SafeFs.AssertFile(SafeFs.Under(destination,copied.relative),copied.sha256,copied.bytes);
            }
            return true;
        }

        static Version PublicVersion(string id) {
            if(id==null||!id.StartsWith("gtavxr-",StringComparison.Ordinal))return null;
            var pieces=id.Substring(7).Split('-');
            Version version;
            if(pieces.Length!=3||!Version.TryParse(String.Join(".",pieces),out version))return null;
            return "gtavxr-"+version.ToString(3).Replace('.','-')==id?version:null;
        }

        IEnumerable<VersionManifest> Versions() {
            foreach(string file in Directory.EnumerateFiles(env.Dir("versions"),"*.json")){
                var version=Json.Read<VersionManifest>(file);
                if(version==null||version.schema!="gtavxr-suite2-version-v1"||version.id!=Path.GetFileNameWithoutExtension(file))
                    throw new InvalidDataException("Invalid version record: "+file);
                yield return version;
            }
        }

        IEnumerable<Profile> Profiles() {
            foreach(string directory in Directory.EnumerateDirectories(env.Dir("profiles"))){
                SafeFs.NoLinks(directory);
                string id=Path.GetFileName(directory);
                var profile=library.Profile(id);
                if(profile==null)continue;
                if(profile.id!=id||profile.schema!="gtavxr-suite2-profile-v1")
                    throw new InvalidDataException("Invalid profile record: "+directory);
                yield return profile;
            }
        }

        internal void CheckDowngrade(string target) {
            var current=PublicVersion(target);
            var installed=new GameLayer(env).State();
            CheckPublicGamePaths(env,installed);
            if(Versions().Any(v=>v.embedded_release&&PublicVersion(v.id)>current)||
               (installed!=null&&PublicVersion(installed.version)>current))
                throw new InvalidOperationException("A newer GTAVXR release is already installed.");
        }

        internal static bool HasPrevious(string target,IEnumerable<VersionManifest> versions,IEnumerable<Profile> profiles) {
            var current=PublicVersion(target);
            return versions.Any(v=>v.embedded_release&&PublicVersion(v.id)!=null&&PublicVersion(v.id)<current)||
                profiles.Any(p=>KnownMissingRelease(p.version,target));
        }

        Journal Plan(VersionManifest target,string selected) {
            if(Pending)return Read(target);
            var current=PublicVersion(target.id);
            var versions=Versions().ToList();
            var retired=versions.Where(v=>v.embedded_release&&PublicVersion(v.id)!=null&&PublicVersion(v.id)<current).ToList();
            var ids=new HashSet<string>(retired.Select(v=>v.id),StringComparer.Ordinal);
            var all=Profiles().ToList();
            var known=new HashSet<string>(versions.Select(v=>v.id),StringComparer.Ordinal);
            var profiles=all.Where(p=>ids.Contains(p.version)||(!known.Contains(p.version)&&KnownMissingRelease(p.version,target.id)))
                .ToDictionary(p=>p.id,p=>p.version,StringComparer.Ordinal);
            if(retired.Count==0&&profiles.Count==0)return null;
            var chosen=all.FirstOrDefault(p=>p.id==selected&&(profiles.ContainsKey(p.id)||p.version==target.id))??
                       all.FirstOrDefault(p=>profiles.ContainsKey(p.id)||p.version==target.id);
            return new Journal{target=target.id,bundle=target.source_sha256,game=SafeFs.Root(env.GameDir),
                selected=chosen==null?null:chosen.id,profiles=profiles,retired=retired};
        }

        internal string SelectProfile(VersionManifest target,string selected) {
            var plan=Plan(target,selected);
            return plan==null?null:plan.selected;
        }

        internal void Prepare(VersionManifest target,string selected) {
            if(Pending){Read(target);return;}
            var plan=Plan(target,selected);
            if(plan!=null)Json.PublishNew(path,plan);
        }

        static bool KnownMissingRelease(string id,string target) {
            return (id==EmbeddedRelease.PreviousVersionId||id=="gtavxr-1-0-1")&&PublicVersion(id)<PublicVersion(target);
        }

        Journal Read(VersionManifest target) {
            var journal=Json.Read<Journal>(path);
            if(journal==null||journal.target!=target.id||journal.bundle!=target.source_sha256||
               !String.Equals(journal.game,SafeFs.Root(env.GameDir),StringComparison.OrdinalIgnoreCase)||
               journal.retired==null||journal.profiles==null||
               journal.retired.Any(v=>v==null||!v.embedded_release||PublicVersion(v.id)==null||
                                      PublicVersion(v.id)>=PublicVersion(target.id)))
                throw new InvalidDataException("The unfinished update belongs to a different game folder or installer.");
            return journal;
        }

        internal void Finish(VersionManifest target) {
            if(!Pending)return;
            var journal=Read(target);
            var layer=new GameLayer(env);
            var installed=layer.State();
            if(layer.Pending||installed==null||installed.version!=target.id||layer.Verify().Count!=0)
                throw new InvalidDataException("The updated game files have not been verified.");
            var unfinished=new PlaySession(env).Unfinished();
            if(unfinished.Count!=0)throw new InvalidOperationException("RECOVERY_REQUIRED");
            var obsolete=new HashSet<string>(journal.retired.Select(v=>v.id).Concat(journal.profiles.Values),StringComparer.Ordinal);
            if(obsolete.Any(id=>PublicVersion(id)==null||PublicVersion(id)>=PublicVersion(target.id)))
                throw new InvalidDataException("Unexpected release in the migration journal.");
            foreach(var entry in journal.profiles){
                var profile=library.Profile(entry.Key);
                if(profile==null||(profile.version!=entry.Value&&profile.version!=target.id))
                    throw new InvalidDataException("Profile changed during the update: "+entry.Key);
                if(profile.version==target.id)continue;
                // Change only version, including in profiles with fields unknown to this release.
                string file=SafeFs.Under(library.ProfileDir(entry.Key),"profile.json");
                var data=Json.Read<Dictionary<string,object>>(file);
                data["version"]=target.id;
                Json.Atomic(file,data);
            }
            if(Profiles().Any(p=>obsolete.Contains(p.version)))
                throw new InvalidDataException("A profile still uses a previous release.");

            var reachable=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach(var version in Versions().Where(v=>!obsolete.Contains(v.id)))
                foreach(var hash in Hashes(version))reachable.Add(hash);
            foreach(string file in Directory.EnumerateFiles(env.Dir("mods"),"*.json")){
                var mod=Json.Read<ModManifest>(file);
                if(mod==null||mod.schema!="gtavxr-suite2-mod-v1"||mod.id!=Path.GetFileNameWithoutExtension(file))
                    throw new InvalidDataException("Invalid mod record: "+file);
                var files=Refs(mod.files).Concat(Refs(mod.script_files)).Concat(Refs(mod.asi_files)).Concat(Refs(new[]{mod.archive}));
                foreach(var item in files)reachable.Add(item.sha256);
            }
            foreach(var item in installed.files)reachable.Add(item.sha256);
            foreach(var version in journal.retired)RemoveRuntime(version);
            foreach(string id in obsolete) {
                Ids.Check(id);
                SafeFs.DeleteName(SafeFs.Under(env.DataRoot,"embedded/"+id+".json"));
                SafeFs.DeleteName(SafeFs.Under(env.DataRoot,"versions/"+id+".json"));
            }
            var blobs=new Blobs(env);
            foreach(string hash in journal.retired.SelectMany(Hashes).Distinct(StringComparer.OrdinalIgnoreCase))
                if(!reachable.Contains(hash)){
                    string file=blobs.PathOf(hash);
                    if(File.Exists(file)){
                        if(!String.Equals(SafeFs.Hash(file),hash,StringComparison.OrdinalIgnoreCase))
                            throw new InvalidDataException("Previous release blob changed: "+file);
                        SafeFs.DeleteName(file);
                    }
                }
            SafeFs.DeleteName(path);
        }

        void RemoveRuntime(VersionManifest version) {
            string root=SafeFs.Under(env.DataRoot,"runtime/"+version.id);
            if(!Directory.Exists(root))return;
            var paths=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach(var file in Refs(version.runtime)){
                string target=SafeFs.Under(root,file.path);
                paths.Add(target);
                if(File.Exists(target))SafeFs.AssertFile(target,file.sha256,file.bytes);
            }
            RemoveRuntimeDirectory(root,paths);
        }

        static void RemoveRuntimeDirectory(string root,HashSet<string> paths) {
            foreach(string directory in Directory.GetDirectories(root)){
                SafeFs.NoLinks(directory);
                RemoveRuntimeDirectory(directory,paths);
            }
            foreach(string file in Directory.GetFiles(root)){
                SafeFs.NoLinks(file);
                if(!paths.Contains(file))throw new InvalidDataException("Unexpected previous runtime file. Move it out and retry: "+file);
                SafeFs.DeleteName(file);
            }
            Directory.Delete(root);
        }

        static IEnumerable<FileRef> Refs(IEnumerable<FileRef> files) {
            return (files??Enumerable.Empty<FileRef>()).Where(f=>f!=null);
        }

        static IEnumerable<string> Hashes(VersionManifest version) {
            return Refs(version.files).Concat(Refs(version.runtime)).Concat(Refs(version.replaces))
                .Concat(Refs(new[]{version.vr_settings_seed})).Select(f=>f.sha256)
                .Concat((version.replaces??new List<ReplaceRef>()).Select(f=>f.original_sha256))
                .Where(SafeFs.IsHash);
        }
    }
}
