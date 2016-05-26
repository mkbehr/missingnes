cmake_minimum_required(VERSION 2.8)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE "DEBUG")
  #set(CMAKE_BUILD_TYPE "RELEASE")
  #set(CMAKE_BUILD_TYPE "RELWITHDEBINFO")
  #set(CMAKE_BUILD_TYPE "MINSIZEREL")
endif()

set(CMAKE_CXX_COMPILER g++)

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

find_package(Boost 1.60.0)
if(Boost_FOUND)
  # TODO make less platform-specific
  include_directories("${Boost_INCLUDE_DIRS}" ${GLFW_INCLUDE_DIRS} "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.11.sdk/System/Library/Frameworks/Python.framework/Versions/2.7/include/python2.7/")
  message("${GLFW_LIBRARY_DIRS}")
  link_directories("${GLFW_LIBRARY_DIRS}")
  set(Boost_USE_STATIC_LIBS OFF)
  set(Boost_USE_MULTITHREADED ON)
  set(Boost_USE_STATIC_RUNTIME OFF)
  find_package(Boost 1.60.0 COMPONENTS python)


  if (NOT Python_FRAMEWORK)
     message(FATAL_ERROR "Python not found")
  endif()

  add_library(screen MODULE screen.cpp)
  message(${GLFW_LIBRARIES})
  target_link_libraries(screen
    ${Boost_LIBRARIES} ${GLFW_LIBRARIES}
    ${Python_FRAMEWORK} ${Cocoa_FRAMEWORK} ${OpenGL_FRAMEWORK}
    ${IOKit_FRAMEWORK} ${CoreFoundation_FRAMEWORK} ${CoreVideo_FRAMEWORK}
    )

elseif(NOT Boost_FOUND)
  message(FATAL_ERROR "Unable to find correct Boost version. Did you set BOOST_ROOT?")
endif()
