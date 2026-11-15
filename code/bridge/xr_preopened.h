#pragma once
#include <string>

namespace native_xr {
inline bool steamvr_bootstrap_requested(){
    wchar_t value[4]={};
    return GetEnvironmentVariableW(L"GTAVXR_STEAMVR_BOOTSTRAP",value,4)==1&&value[0]==L'1';
}
inline bool steamvr_runtime(const char* name){
    return name&&!_strnicmp(name,"SteamVR",7)&&
        (name[7]==0||name[7]=='/'||name[7]==' ');
}

// The runtime-owned instance and loader reference move together exactly once.
// A prepared instance has only a system. D3D binding/session stay on the
// existing engine initialization path and the normal session owns teardown.
struct PreopenedXr {
    OpenXrApi api{};
    XrInstance instance=XR_NULL_HANDLE;
    XrSystemId system=XR_NULL_SYSTEM_ID;
    std::wstring loader;

    bool take(const wchar_t* path,OpenXrApi& destination,XrInstance& xr,XrSystemId& id){
        if(!instance||!system||!path||loader!=path||destination.module||xr||id)return false;
        destination=api;xr=instance;id=system;
        api={};instance=XR_NULL_HANDLE;system=XR_NULL_SYSTEM_ID;loader.clear();
        return true;
    }
};
}
