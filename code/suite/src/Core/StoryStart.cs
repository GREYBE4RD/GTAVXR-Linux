using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace GtavxrSuite {
    internal sealed class StoryStart {
        internal const string NewStory="new";
        internal const string Archive="StoryArchive/";
        static readonly StringComparer Paths=StringComparer.OrdinalIgnoreCase;
        internal string choice;
        internal SaveFileRef source;

        internal static bool Slot(string relative) {
            var parts=relative.Split('/');
            string name=parts.Last();
            int slot;
            if(!SaveInfo.IsStorySlot(name)||!Int32.TryParse(name.Substring(5),out slot)||slot>15)return false;
            return (parts.Length==2&&Paths.Equals(parts[0],"Default"))||
                   (parts.Length==3&&(Paths.Equals(parts[0],"Profiles")||Paths.Equals(parts[0],"StoryArchive")));
        }

        internal static bool SlotOrBackup(string relative) {
            return Slot(relative.EndsWith(".bak",StringComparison.OrdinalIgnoreCase)?
                        relative.Substring(0,relative.Length-4):relative);
        }

        internal static IEnumerable<SaveFileRef> Choices(Profile profile) {
            var files=(profile.user??new List<SaveFileRef>()).Where(file=>SlotOrBackup(file.relative))
                .ToDictionary(file=>file.relative,Paths);
            return files.Values.Where(file=>{
                if(Slot(file.relative))return true;
                SaveFileRef main;
                return !files.TryGetValue(file.relative.Substring(0,file.relative.Length-4),out main)||
                       !Paths.Equals(main.sha256,file.sha256);
            });
        }

        internal static void Select(Profile profile,string choice) {
            if(choice!=null&&choice!=NewStory&&!Choices(profile).Any(file=>Paths.Equals(file.relative,choice)))
                throw new InvalidDataException("STORY_SAVE_MISSING: "+choice);
            profile.story_start=choice;
        }

        internal static void Import(string retail,string user,Profile profile) {
            AddSaves(retail,user,profile,Choices(new Profile{user=UserTree.Snapshot(retail,true)}));
        }

        internal static void ImportFromProfile(string from,string user,Profile profile,Profile source) {
            if(!Directory.Exists(from))throw new DirectoryNotFoundException(from);
            AddSaves(from,user,profile,Choices(source));
        }

        static void AddSaves(string source,string user,Profile profile,IEnumerable<SaveFileRef> saves) {
            var files=(profile.user??new List<SaveFileRef>()).ToDictionary(file=>file.relative,Paths);
            var additions=new List<KeyValuePair<SaveFileRef,SaveFileRef>>();
            foreach(var save in saves){
                SaveFileRef existing;
                if(files.TryGetValue(save.relative,out existing)&&Paths.Equals(existing.sha256,save.sha256))continue;
                string relative=existing==null?save.relative:Archive+"import-"+save.sha256+"/"+Path.GetFileName(save.relative);
                if(files.ContainsKey(relative))continue;
                var target=new SaveFileRef{relative=relative,sha256=save.sha256,bytes=save.bytes};
                files.Add(relative,target);
                additions.Add(new KeyValuePair<SaveFileRef,SaveFileRef>(save,target));
            }
            SafeFs.Budget(user,additions.Sum(pair=>pair.Value.bytes));
            foreach(var pair in additions){
                var save=pair.Key;var target=pair.Value;
                string path=SafeFs.Under(user,target.relative);
                if(File.Exists(path))SafeFs.AssertFile(path,target.sha256,target.bytes);
                else SafeFs.ReplaceFrom(SafeFs.Under(source,save.relative),path,target.sha256,target.bytes,0);
            }
            profile.user=files.Values.ToList();
        }

        internal static StoryStart Resolve(Profile profile) {
            var choices=Choices(profile).ToList();
            if(profile.story_start==NewStory)return new StoryStart{choice=NewStory};
            if(profile.story_start!=null) {
                var selected=choices.FirstOrDefault(file=>Paths.Equals(file.relative,profile.story_start));
                if(selected==null)throw new InvalidDataException("STORY_SAVE_MISSING: "+profile.story_start);
                return new StoryStart{choice=selected.relative,source=selected};
            }
            // Preserve the previous automatic choice on migrated profiles.
            if(SaveInfo.HasLocalStory(choices))return new StoryStart();
            var accounts=SaveInfo.RetailAccounts(choices);
            if(accounts.Count>1&&!accounts.Contains(profile.imported_save_account))
                throw new InvalidDataException("STORY_SELECT_SAVE");
            return new StoryStart();
        }

        internal static List<SaveFileRef> Stage(string user,string destination,List<SaveFileRef> files,StoryStart plan) {
            var keep=files.Where(file=>!SlotOrBackup(file.relative)&&
                !Path.GetFileName(file.relative).StartsWith("MISREP0000",StringComparison.OrdinalIgnoreCase)).ToList();
            if(plan.source!=null)UserTree.Verify(user,new List<SaveFileRef>{plan.source});
            UserTree.Mirror(user,keep,destination,true);
            var staged=new List<SaveFileRef>();
            if(plan.source!=null){
                var source=plan.source;
                string name=Path.GetFileName(source.relative);
                if(name.EndsWith(".bak",StringComparison.OrdinalIgnoreCase))name=name.Substring(0,name.Length-4);
                var target=new SaveFileRef{relative="Default/"+name,sha256=source.sha256,bytes=source.bytes};
                SafeFs.CopyNew(SafeFs.Under(user,source.relative),SafeFs.Under(destination,target.relative),target.sha256,target.bytes);
                staged.Add(target);
            }
            return staged;
        }

        internal static List<SaveFileRef> Capture(string live,string user,string history,Profile profile,SessionRecord session,List<SaveFileRef> now) {
            var initial=session.story_staged??new List<SaveFileRef>();
            var changes=now.Where(file=>SlotOrBackup(file.relative)&&
                !initial.Any(before=>Paths.Equals(before.relative,file.relative)&&Paths.Equals(before.sha256,file.sha256))).ToList();
            var current=UserTree.Snapshot(user,true).ToDictionary(file=>file.relative,Paths);
            var archives=(profile.user??new List<SaveFileRef>()).Where(file=>
                file.relative.StartsWith(Archive,StringComparison.OrdinalIgnoreCase)).ToDictionary(file=>file.relative,Paths);
            // Capture may resume after replacing a slot but before updating profile.json. The copy here is immutable.
            var baseline=session.story_before??new List<SaveFileRef>();
            // If Play used a different save in this slot, the engine can write a backup of those temporary bytes.
            // Only retain a backup alongside genuine progress from this session.
            changes=changes.Where(file=>!file.relative.EndsWith(".bak",StringComparison.OrdinalIgnoreCase)||
                changes.Any(main=>Paths.Equals(main.relative+".bak",file.relative))).ToList();
            foreach(var file in changes){
                var before=baseline.FirstOrDefault(old=>Paths.Equals(old.relative,file.relative));
                if(before==null||Paths.Equals(before.sha256,file.sha256))continue;
                if(!Paths.Equals(session.story_start,StoryStart.NewStory)&&
                   Paths.Equals(session.story_start,file.relative))continue;
                if(Paths.Equals(session.story_start+".bak",before.relative))continue;
                string archived=Archive+session.id+"/"+Path.GetFileName(before.relative);
                if(before.relative.StartsWith("Profiles/",StringComparison.OrdinalIgnoreCase))
                    archived=Archive+session.id+"-"+before.relative.Split('/')[1]+"/"+Path.GetFileName(before.relative);
                string target=SafeFs.Under(user,archived);
                if(!File.Exists(target))
                    SafeFs.CopyNew(SafeFs.Under(history,before.relative),target,before.sha256,before.bytes);
                else SafeFs.AssertFile(target,before.sha256,before.bytes);
                archives[archived]=new SaveFileRef{relative=archived,sha256=before.sha256,bytes=before.bytes};
            }
            foreach(var file in now.Where(row=>!SlotOrBackup(row.relative)).Concat(changes)){
                SafeFs.ReplaceFrom(SafeFs.Under(live,file.relative),SafeFs.Under(user,file.relative),file.sha256,file.bytes,0);
                current[file.relative]=file;
            }
            var resume=changes.Where(file=>Slot(file.relative)).OrderByDescending(file=>
                File.GetLastWriteTimeUtc(SafeFs.Under(live,file.relative))).ThenBy(file=>file.relative,Paths).FirstOrDefault();
            if(resume!=null)profile.story_start=resume.relative;
            return current.Values.Concat(archives.Values)
                .Concat((profile.user??new List<SaveFileRef>()).Where(file=>!UserTree.IsStoryData(file.relative)&&
                        !file.relative.StartsWith(Archive,StringComparison.OrdinalIgnoreCase))).ToList();
        }
    }
}
