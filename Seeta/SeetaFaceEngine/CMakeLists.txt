cmake_minimum_required(VERSION 3.2.0)

project(seeta_face)

set(CMAKE_BUILD_TYPE "Release")
set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS} -std=c++11 -O2")
set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS} -std=c++11 -O2 -g -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -msse4.1")


add_subdirectory(FaceDetection)
add_subdirectory(FaceAlignment)
add_subdirectory(FaceIdentification)
