using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;

namespace GtavxrSuite {
    internal static class ReleaseLifecycleTests {
        static void Check(bool ok,string what) {
            if(!ok)throw new InvalidDataException("Lifecycle fixture: "+what);
        }

        static FileRef Blob(Env env,string name,string text) {
            string source=SafeFs.Under(env.DataRoot,"fixture-"+name);
            File.WriteAllText(source,text);
            var result=new Blobs(env).PutFile(source,name);
            File.Delete(source);
            return result;
        }

        internal static void Migration(string root) {
            var env=Env.ForFixture(root);
            var lib=new Library(env);
            var oldFile=Blob(env,"fixture-old.bin","old build");
            var shared=Blob(env,"fixture-shared.bin","shared resource");
            var newFile=Blob(env,"fixture-next.bin","new build");
            var oldRuntime=Blob(env,"old-runtime.dll","old bridge");
            var old=new VersionManifest{id="gtavxr-1-0-0",embedded_release=true,files=new List<FileRef>{oldFile,shared},
                runtime=new List<FileRef>{oldRuntime},source_sha256=oldFile.sha256};
            var next=new VersionManifest{id=EmbeddedRelease.VersionId,embedded_release=true,files=new List<FileRef>{newFile,shared},
                runtime=new List<FileRef>(),source_sha256=newFile.sha256};
            lib.SaveVersion(old);
            lib.SaveVersion(next);
            lib.SaveVersion(new VersionManifest{id="172",files=new List<FileRef>{shared}});
            string runtime=SafeFs.Under(env.Dir("runtime/"+old.id),oldRuntime.path);
            new Blobs(env).Materialize(oldRuntime,runtime);
            var p1=new Profile{id="first",version=old.id,name="First"};
            var p2=new Profile{id="second",version=old.id,name="Second",mods=new List<string>{"retained-mod"}};
            lib.SaveProfile(p1);lib.SaveProfile(p2);
            lib.SaveProfile(new Profile{id="dev",version="172",name="Dev"});
            lib.SaveMod(new ModManifest{id="retained-mod",archive=shared});
            string profile=SafeFs.Under(lib.ProfileDir(p2.id),"profile.json");
            var extra=Json.Read<Dictionary<string,object>>(profile);
            extra["custom-setting"]="keep this";
            Json.Atomic(profile,extra);
            string save=SafeFs.Under(lib.UserDir(p2.id),"SGTA50000");
            File.WriteAllText(save,"retained story data");
            string saveHash=SafeFs.Hash(save);
            string comparison=env.Dir("scratch/profile-comparison");
            UserTree.CopyInto(lib.ProfileDir(p2.id),UserTree.Snapshot(lib.ProfileDir(p2.id)),comparison);
            Check(DataLocation.SameProfileFiles(lib.ProfileDir(p2.id),comparison),"an exact copy of the profile matches");
            string otherSave=SafeFs.Under(comparison,"user/SGTA50000");
            File.WriteAllText(otherSave,"Retained story data");
            Check(!DataLocation.SameProfileFiles(lib.ProfileDir(p2.id),comparison),"same-size changed save is detected");
            var layer=new GameLayer(env);
            layer.Apply(old,new List<ModManifest>(),null,false);
            var migration=new ReleaseMigration(env);
            Check(migration.SelectProfile(next,p2.id)==p2.id,"selected profile retained");
            migration.Prepare(next,p2.id);
            try { migration.Finish(next);throw new Exception("premature cleanup"); }
            catch(InvalidDataException) {}
            Check(File.Exists(runtime)&&lib.Version(old.id)!=null,"old files survive until target verified");
            layer.Apply(next,new List<ModManifest>(),null,false);
            new ReleaseMigration(env).Finish(next);
            new ReleaseMigration(env).Finish(next);
            Check(lib.Profile(p1.id).version==next.id&&lib.Profile(p2.id).version==next.id&&lib.Profile("dev").version=="172",
                "two public profiles migrate in place and internal profile stays");
            Check(lib.Profiles().Count==3&&SafeFs.Hash(save)==saveHash&&
                  (string)Json.Read<Dictionary<string,object>>(profile)["custom-setting"]=="keep this",
                "no duplicate profiles, changed save, or lost unknown settings");
            var store=new Blobs(env);
            Check(!migration.Pending&&lib.Version(old.id)==null&&!File.Exists(runtime)&&
                !File.Exists(store.PathOf(oldFile.sha256))&&File.Exists(store.PathOf(shared.sha256))&&
                !File.Exists(SafeFs.Under(env.GameDir,oldFile.path))&&File.Exists(SafeFs.Under(env.GameDir,newFile.path)),
                "only exclusive old files are removed");
        }

        internal static void Removal(string root) {
            var env=Env.ForFixture(root);
            var lib=new Library(env);
            var made=Blob(env,"fixture-owned.dll","GTAVXR");
            var version=new VersionManifest{id="gtavxr-1-0-0",files=new List<FileRef>{made}};
            lib.SaveVersion(version);
            new GameLayer(env).Apply(version,new List<ModManifest>(),null,false);
            string normal=SafeFs.Under(env.GameDir,"GTA5.exe");
            string save=SafeFs.Under(env.UserDataDir,"player-save");
            File.WriteAllText(normal,"retail");
            File.WriteAllText(save,"normal story");
            var location=new DataLocation(env.DataRoot);
            var roots=CompleteRemoval.Libraries(env,location);
            string aside=env.Dir("sessions/removal-fixture/aside");
            string kept=SafeFs.Under(aside,"user-plugin.asi");
            File.WriteAllText(kept,"player file stored during recovery");
            try { CompleteRemoval.RemoveData(env,location,roots);throw new Exception("removed retained player file"); }
            catch(IOException error){Check(error.Message.Contains(aside),"identify retained player files");}
            Check(File.Exists(kept)&&File.Exists(SafeFs.Under(env.GameDir,made.path)),"removal leaves both layers intact while recovery files remain");
            File.Move(kept,SafeFs.Under(env.GameDir,"user-plugin.asi"));
            CompleteRemoval.RemoveData(env,location,roots);
            Check(!Directory.Exists(env.DataRoot)&&!File.Exists(SafeFs.Under(env.GameDir,made.path))&&
                File.ReadAllText(normal)=="retail"&&File.ReadAllText(save)=="normal story"&&
                File.Exists(SafeFs.Under(env.GameDir,"user-plugin.asi")),"full data cleanup preserves GTA, regular saves and player files");
        }

        internal static void MovedGame(string root) {
            var env=Env.ForFixture(root);
            var lib=new Library(env);
            var payload=Blob(env,"fixture-owned.dll","GTAVXR");
            env.RetailOverride=new Dictionary<string,string>();
            Directory.CreateDirectory(SafeFs.Under(env.GameDir,"update"));
            foreach(string file in new[]{"GTA5.exe","update/update.rpf","update/update2.rpf"}){
                string retail=SafeFs.Under(env.GameDir,file);
                File.WriteAllText(retail,"retail base "+file);
                env.RetailOverride.Add(file,SafeFs.Hash(retail));
            }
            var v=new VersionManifest{id="relocate",files=new List<FileRef>{payload}};
            lib.SaveVersion(v);
            var layer=new GameLayer(env);
            layer.Apply(v,new List<ModManifest>(),null,false);
            string original=env.GameDir,moved=original+"-moved";
            Directory.Move(original,moved);
            string owned=SafeFs.Under(moved,payload.path);
            File.WriteAllText(owned,"foreign bytes");
            try{layer.Relocate(moved);throw new Exception("accepted changed payload");}
            catch(InvalidDataException){}
            Check(layer.State().game_dir==original&&File.ReadAllText(owned)=="foreign bytes","failed relocation leaves both records and files intact");
            new Blobs(env).Materialize(payload,owned);
            layer.Relocate(moved);
            Check(layer.State().game_dir==moved&&layer.Verify().Count==0,"relocation adopts verified files at the new location");
            env.GameDir=moved;
            string unknown=SafeFs.Under(moved,"similar-owned.dll");
            File.WriteAllText(unknown,"external");
            var location=new DataLocation(env.DataRoot);
            var destinations=CompleteRemoval.Libraries(env,location);
            using(var scope=GameScope.Acquire(moved)){
                try{CompleteRemoval.RemoveData(env,location,destinations);throw new Exception("uninstalled locked game");}
                catch(IOException){}
                Check(File.Exists(owned)&&Directory.Exists(env.DataRoot),"busy install survives removal");
            }
            try{layer.Uninstall((step,done,total)=>{throw new IOException("interrupted uninstall");});throw new Exception("expected interruption");}
            catch(IOException error){Check(error.Message=="interrupted uninstall","simulated removal interrupt");}
            Check(layer.Pending,"uninstall journal retained");
            CompleteRemoval.RemoveData(env,location,destinations);
            Check(File.Exists(SafeFs.Under(moved,"GTA5.exe"))&&File.Exists(unknown)&&!File.Exists(owned)
                  &&!Directory.Exists(env.DataRoot),"moved game cleanup retires only owned content");
        }

        internal static void DivergentLibraries(string root) {
            var prior=Env.ForFixture(root);
            prior.SaveSettings(prior.LoadSettings());
            var original=new Library(prior);
            var old=new Profile{id="same-profile",version=EmbeddedRelease.PreviousVersionId};
            string oldUser=original.UserDir(old.id);
            string slot="Default/SGTA50015";
            string oldFile=SafeFs.Under(oldUser,slot);
            Directory.CreateDirectory(Path.GetDirectoryName(oldFile));
            File.WriteAllText(oldFile,"Earlier campaign");
            old.user=UserTree.Snapshot(oldUser,true);
            original.SaveProfile(old);
            string active=Path.Combine(root,"Active library");
            var location=new DataLocation(prior.DataRoot);
            location.CopyAndSelect(prior,active);
            var env=Env.Product(active);
            env.GameDir=prior.GameDir;
            var library=new Library(env);
            var current=library.Profile(old.id);
            string activeFile=SafeFs.Under(library.UserDir(current.id),slot);
            File.WriteAllText(activeFile,"Different campaign");
            current.user=UserTree.Snapshot(library.UserDir(current.id),true);
            library.SaveProfile(current);
            var migration=new ReleaseMigration(env);
            var version=new VersionManifest{id=EmbeddedRelease.VersionId,embedded_release=true};
            try{migration.CheckLibraries(version,current.id,location);throw new Exception("divergent save was ignored");}
            catch(IOException error){Check(error.Message.Contains(old.id),"reported the differing source profile");}
            new Importers(env).MergeStorySaves(current.id,prior.DataRoot,old.id);
            migration.CheckLibraries(version,current.id,location);
            Check(File.ReadAllText(activeFile)=="Different campaign"&&File.ReadAllText(oldFile)=="Earlier campaign"&&
                  library.Profile(current.id).user.Any(file=>file.relative.StartsWith(StoryStart.Archive)&&file.sha256==SafeFs.Hash(oldFile)),
                  "migration can continue after the verified merge preserves both saves");
        }

        internal static void Channel(string root) {
            const string tag="v1.0.3";
            string hash=new string('A',64);
            string json=Json.Encode(new{tag_name=tag,draft=false,prerelease=false,assets=new[]{
                new{name="GTAVXR.exe",state="uploaded",size=1234,digest="sha256:"+hash,
                    browser_download_url=PublicReleaseChannel.Releases+"/download/"+tag+"/GTAVXR.exe"}
            }});
            Check(PublicReleaseChannel.Parse(json,new Version("1.0.2")).Hash==hash,"official newer release with hash");
            Check(PublicReleaseChannel.Parse(json,new Version("1.0.3"))==null,"current release");
            try{PublicReleaseChannel.Parse(json.Replace("github.com","example.com"),new Version("1.0.2"));
                throw new Exception("accepted untrusted endpoint");}
            catch(InvalidDataException){}
            Directory.CreateDirectory(root);
            string file=SafeFs.Under(root,"GTAVXR.exe");
            File.WriteAllText(file,"isolated asset");
            var update=new PublicReleaseChannel.Update{Hash=SafeFs.Hash(file),Bytes=new FileInfo(file).Length};
            PublicReleaseChannel.VerifyDownload(update,file);
            File.WriteAllText(file,"Isolated asset");
            try{PublicReleaseChannel.VerifyDownload(update,file);throw new Exception("accepted changed download");}
            catch(InvalidDataException){}
        }

        internal static object FromPublic100(string root) {
            root=SafeFs.Root(root);
            if(!String.Equals(Path.GetFileName(root),"FIXTURE-PUBLIC-100",StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Expected an isolated fixture root.");
            string library=SafeFs.Under(root,"suite-data");
            string marker=SafeFs.Under(library,"versions/gtavxr-1-0-0.json");
            if(!File.Exists(marker)||!File.Exists(SafeFs.Under(root,"game/GTA5.exe")))
                throw new InvalidDataException("Expected the owned official 1.0.0 fixture.");
            var env=Env.ForFixture(root);
            var store=new Library(env);
            var before=store.Profiles().ToList();
            Check(before.Count>0&&before.All(p=>p.version=="gtavxr-1-0-0"),"public fixture profiles");
            var copy=before[0];
            new Importers(env).Duplicate(copy.id,"Second public profile");
            before=store.Profiles().ToList();
            var hashes=before.ToDictionary(p=>p.id,p=>UserTree.Snapshot(store.UserDir(p.id))
                .ToDictionary(f=>f.relative,f=>f.sha256));
            var session=new PlaySession(env);
            var layer=new GameLayer(env);
            string picked=before[0].id;
            try {
                session.InstallEmbedded(picked,step=>{
                    if(layer.Pending&&step.step=="game"&&step.done>0)
                        throw new IOException("FIXTURE_INTERRUPTED_UPDATE");
                },System.Threading.CancellationToken.None);
                throw new InvalidOperationException("Expected interruption.");
            } catch(IOException error) { if(error.Message!="FIXTURE_INTERRUPTED_UPDATE")throw; }
            Check(layer.Pending&&new ReleaseMigration(env).Pending&&File.Exists(marker),"migration survives interrupted deployment");
            Check(session.Recover()=="OK","game-layer recovery");
            Check(session.InstallEmbedded(picked,null,System.Threading.CancellationToken.None)==picked,"resume preserves selected ID");
            Check(store.Profiles().Count==before.Count&&store.Profiles().All(p=>p.version==EmbeddedRelease.VersionId),
                "all profiles migrate without duplication");
            foreach(var entry in hashes)
                Check(UserTree.Snapshot(store.UserDir(entry.Key)).All(f=>entry.Value.ContainsKey(f.relative)&&entry.Value[f.relative]==f.sha256)&&
                      UserTree.Snapshot(store.UserDir(entry.Key)).Count==entry.Value.Count,"all story files survive unchanged");
            Check(!File.Exists(marker)&&!Directory.Exists(SafeFs.Under(library,"runtime/gtavxr-1-0-0"))&&
                !new ReleaseMigration(env).Pending&&layer.Verify().Count==0,"old version removed and replacement verified");
            string retail=SafeFs.Under(root,"game/GTA5.exe");
            string hash=SafeFs.Hash(retail);
            var location=new DataLocation(env.DataRoot);
            CompleteRemoval.RemoveData(env,location,CompleteRemoval.Libraries(env,location));
            Check(!Directory.Exists(library)&&SafeFs.Hash(retail)==hash&&
                  !File.Exists(SafeFs.Under(root,"game/GTAVXR_SourceBaseline.exe")),"complete deletion preserves retail");
            return new{status="PASS_MISSION_SAFE_RELEASE_MIGRATION",profiles=before.Count,interrupted=true,
                complete_data_removal=true,gta_launched=false,real_game_touched=false};
        }
    }
}
