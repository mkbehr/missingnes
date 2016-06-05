cmake_minimum_required(VERSION 3.1)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE "DEBUG")
  #set(CMAKE_BUILD_TYPE "RELEASE")
  #set(CMAKE_BUILD_TYPE "RELWITHDEBINFO")
  #set(CMAKE_BUILD_TYPE "MINSIZEREL")
endif()

set(CMAKE_CXX_COMPILER g++)
set(CMAKE_CXX_STANDARD 11)

find_package(PythonInterp)
find_package(PythonLibs)

find_package(PkgConfig REQUIRED)
pkg_search_module(GLFW REQUIRED glfw3)

find_library(Python_FRAMEWORK Python)
find_library(Cocoa_FRAMEWORK Cocoa)
find_library(OpenGL_FRAMEWORK OpenGL)
find_library(IOKit_FRAMEWORK IOKit)
find_library(CoreFoundation_FRAMEWORK CoreFoundation)
find_library(CoreVideo_FRAMEWORK CoreVideo)
find_library(OpenAL_FRAMEWORK OpenAL) # might not use this
find_library(CoreAudio_FRAMEWORK CoreAudio)
find_library(CoreMIDI_FRAMEWORK CoreMIDI)

set(Portaudio_FIND_REQUIRED TRUE)
include(cmake_modules/FindPortAudio.cmake)

# TODO make less platform-specific
include_directories(SYSTEM
  ${GLFW_INCLUDE_DIRS}
  "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.11.sdk/System/Library/Frameworks/Python.framework/Versions/2.7/include/python2.7/"
  "/usr/local/include"
  ${PORTAUDIO_INCLUDE_DIRS})
link_directories("${GLFW_LIBRARY_DIRS}" "/usr/local/lib")
if (NOT Python_FRAMEWORK)
  message(FATAL_ERROR "Python not found")
endif()
add_library(screen MODULE screen.cpp)
target_link_libraries(screen
  ${GLFW_LIBRARIES}
  ${Python_FRAMEWORK} ${Cocoa_FRAMEWORK} ${OpenGL_FRAMEWORK}
  ${IOKit_FRAMEWORK} ${CoreFoundation_FRAMEWORK} ${CoreVideo_FRAMEWORK}
  ${OpenAL_FRAMEWORK}
  )

# add_executable(alu alu.cpp)
# target_link_libraries(alu ${OpenAL_FRAMEWORK})

# add_executable(rtsine rtsine.cpp)
# set_target_properties(rtsine PROPERTIES
#   COMPILE_DEFINITIONS "__MACOSX_CORE__")
# target_link_libraries(rtsine
#   ${CoreFoundation_FRAMEWORK} ${CoreAudio_FRAMEWORK} ${CoreMIDI_FRAMEWORK}
#   "stk")

add_library(pulsewave PulseWave.cpp)

add_executable(pulsetest pulsetest.cpp)
add_dependencies(pulsetest pulsewave)
target_link_libraries(pulsetest
  pulsewave
  ${PORTAUDIO_LIBRARIES})

add_library(apu MODULE apu.cpp)
add_dependencies(apu pulsewave)
set_target_properties(apu PROPERTIES
  COMPILE_DEFINITIONS "__MACOSX_CORE__")
target_link_libraries(apu
  pulsewave
  ${CoreFoundation_FRAMEWORK} ${CoreAudio_FRAMEWORK} ${CoreMIDI_FRAMEWORK}
  ${PORTAUDIO_LIBRARIES})
