cmake_minimum_required(VERSION 3.25)
project(gtavxr_linux_fsr_forwarder LANGUAGES CXX)

# This is an alternate copy of GTAVXR's NGX SR forwarder. The upstream
# nvngx.dll_gtavxr_sr.dll remains in the verified release and is not rebuilt.
add_library(gtavxr_fsr_forwarder SHARED ../fsr_forwarder.cpp)
set_target_properties(gtavxr_fsr_forwarder PROPERTIES OUTPUT_NAME "nvngx.dll_gtavxr_sr")
target_compile_features(gtavxr_fsr_forwarder PRIVATE cxx_std_17)
if(MSVC)
    target_compile_options(gtavxr_fsr_forwarder PRIVATE /W4 /EHsc /utf-8)
endif()
target_compile_definitions(gtavxr_fsr_forwarder PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
target_link_libraries(gtavxr_fsr_forwarder PRIVATE user32 advapi32)
