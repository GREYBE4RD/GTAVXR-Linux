using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;

namespace GtavxrSuite {
    // Bounded, read-only witness. It never sends messages to the game or holds up startup.
    internal sealed class StartupTimeline {
        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool IsHungAppWindow(IntPtr window);
        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr window,out uint process);

        private readonly string path;
        private readonly Stopwatch clock=Stopwatch.StartNew();
        private readonly object gate=new object();
        private string state;
        private bool scripts;
        private bool disabled;

        public StartupTimeline(string directory){
            path=Path.Combine(directory,"startup-window.log");
        }

        public void ScriptRegistrationStarted(){
            lock(gate){
                if(disabled||scripts||clock.ElapsedMilliseconds>=180000)return;
                scripts=true;
                Write("script_registration_started");
            }
        }

        public void Observe(Process child){
            lock(gate){
                if(disabled||clock.ElapsedMilliseconds>=180000)return;
                try{
                    child.Refresh();
                    IntPtr window=child.MainWindowHandle;
                    uint owner;
                    string current=window==IntPtr.Zero||GetWindowThreadProcessId(window,out owner)==0||
                        owner!=(uint)child.Id?"no_window":IsHungAppWindow(window)?"not_responding":"responding";
                    if(state==current)return;
                    state=current;
                    Write(current+" cpu_ms="+((long)child.TotalProcessorTime.TotalMilliseconds).ToString(CultureInfo.InvariantCulture));
                }catch(InvalidOperationException){disabled=true;}
                catch(System.ComponentModel.Win32Exception){disabled=true;}
            }
        }

        private void Write(string text){
            try{
                File.AppendAllText(path,DateTime.UtcNow.ToString("o",CultureInfo.InvariantCulture)+" elapsed_ms="+
                    clock.ElapsedMilliseconds.ToString(CultureInfo.InvariantCulture)+" "+text+Environment.NewLine);
            }catch(IOException){disabled=true;}
            catch(UnauthorizedAccessException){disabled=true;}
        }
    }
}
