using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace GtavxrSuite {
    internal static class StoryStartTests {
        static void Check(bool valid,string message) {
            if(!valid)throw new InvalidDataException(message);
        }

        static string Write(string root,string relative,string title) {
            string path=SafeFs.Under(root,relative);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllBytes(path,EngineTests.FakeSave(title,8192));
            return SafeFs.Hash(path);
        }

        internal static void Run(string root) {
            var env=Env.ForFixture(root);
            var library=new Library(env);
            var profile=new Profile{id="story",name="Story",version=EmbeddedRelease.VersionId,mods=new List<string>{"test-mod"}};
            string user=library.UserDir(profile.id);
            string live=env.UserDataDir;
            const string selected="Profiles/BEEF/SGTA50015";
            const string competing="Profiles/ABCD/SGTA50015";
            const string slot="Default/SGTA50015";
            string changes=Write(user,selected,"(Autosave) Changes (22.5%)");
            string franklin=Write(user,competing,"Franklin and Lamar (1.6%)");
            string previous=Write(user,slot,"Earlier VR story (8.3%)");
            profile.user=UserTree.Snapshot(user,true);
            profile.imported_save_account="ABCD";
            profile.story_start=selected;
            library.SaveProfile(profile);
            var plan=StoryStart.Resolve(profile);
            var staged=StoryStart.Stage(user,live,profile.user,plan);
            Check(staged.Single().sha256==changes&&SafeFs.Hash(SafeFs.Under(live,slot))==changes,"exact selected save goes to Default");
            Check(!File.Exists(SafeFs.Under(live,selected))&&!File.Exists(SafeFs.Under(live,competing)),"competing account slots omitted");
            var record=new SessionRecord{id="selected-save",story_start=selected,story_staged=staged,story_before=profile.user};
            library.KeepCopy(profile,"history/"+record.id,record.id,true);
            string history=SafeFs.Under(library.CopyDir(profile.id,"history/"+record.id),"user");
            var finished=StoryStart.Capture(live,user,history,profile,record,UserTree.Snapshot(live,true));
            Check(finished.Any(row=>row.relative==slot&&row.sha256==previous)&&profile.story_start==selected,"leaving without saving keeps all starts");
            string progress=Write(live,slot,"New VR progress (25.0%)");
            var actual=UserTree.Snapshot(live,true);
            finished=StoryStart.Capture(live,user,history,profile,record,actual);
            finished=StoryStart.Capture(live,user,history,profile,record,actual);
            Check(finished.Any(row=>row.relative==slot&&row.sha256==progress)&&profile.story_start==slot,"capture is retryable and continues new progress");
            Check(finished.Any(row=>row.relative==selected&&row.sha256==changes)&&
                  finished.Any(row=>row.relative==competing&&row.sha256==franklin)&&
                  finished.Any(row=>row.relative.StartsWith(StoryStart.Archive)&&row.sha256==previous),
                  "all alternate saves survive collision");
            profile.user=finished;
            StoryStart.Select(profile,StoryStart.NewStory);
            staged=StoryStart.Stage(user,live,profile.user,StoryStart.Resolve(profile));
            Check(staged.Count==0&&!UserTree.Snapshot(live,true).Any(row=>StoryStart.Slot(row.relative)),"new story exposes no slots");
            Check(StoryStart.Choices(profile).Count()==4&&profile.mods.SequenceEqual(new[]{"test-mod"}),"new story retains old saves and mod selection");
            var restored=finished.First(row=>row.relative.StartsWith(StoryStart.Archive));
            StoryStart.Select(profile,restored.relative);
            Check(StoryStart.Stage(user,live,profile.user,StoryStart.Resolve(profile)).Single().sha256==previous,"archived progress can be selected");
            try{StoryStart.Select(profile,"Profiles/ABCD/SGTA50009");throw new Exception("missing save accepted");}
            catch(InvalidDataException){}
            string other=Write(live,selected,"Another save in the same slot (11.1%)");
            StoryStart.Import(live,user,profile);
            int count=profile.user.Count;
            StoryStart.Import(live,user,profile);
            Check(count==profile.user.Count&&profile.user.Any(row=>row.relative==selected&&row.sha256==changes)&&
                  profile.user.Any(row=>row.relative.StartsWith(StoryStart.Archive+"import-")&&row.sha256==other),"import keeps both distinct slot bytes and deduplicates retries");
            string backup=Write(user,"Profiles/ABCD/SGTA50014.bak","Backup only (30.0%)");
            profile.user.Add(UserTree.Snapshot(user,true).Single(row=>row.sha256==backup));
            StoryStart.Select(profile,"Profiles/ABCD/SGTA50014.bak");
            Check(StoryStart.Stage(user,live,profile.user.Where(row=>UserTree.IsStoryData(row.relative)).ToList(),StoryStart.Resolve(profile))
                .Any(row=>row.relative=="Default/SGTA50014"&&row.sha256==backup),"backup-only slot can be started explicitly");

            var source=Env.ForFixture(Path.Combine(root,"other-library"));
            source.SaveSettings(source.LoadSettings());
            var otherLibrary=new Library(source);
            var otherProfile=new Profile{id="old-profile",version=EmbeddedRelease.VersionId};
            string sourceUser=otherLibrary.UserDir(otherProfile.id);
            string alternate=Write(sourceUser,selected,"Earlier portable campaign (15.5%)");
            otherProfile.user=UserTree.Snapshot(sourceUser,true);
            otherLibrary.SaveProfile(otherProfile);
            library.SaveProfile(profile);
            new Importers(env).MergeStorySaves(profile.id,source.DataRoot,otherProfile.id);
            var merged=library.Profile(profile.id);
            Check(merged.mods.SequenceEqual(profile.mods)&&merged.story_start==profile.story_start&&
                merged.user.Any(row=>row.sha256==alternate&&row.relative.StartsWith(StoryStart.Archive))&&
                SafeFs.Hash(SafeFs.Under(sourceUser,selected))==alternate,"merging saves preserves both libraries and current profile settings");
        }
    }
}
