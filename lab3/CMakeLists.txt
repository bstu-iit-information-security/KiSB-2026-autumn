cmake_minimum_required(VERSION 3.10)
project(kisb_lab3 CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(kisb_lab3 src/main.cpp src/belt.cpp src/modes.cpp)

if(MSVC)
    target_compile_options(kisb_lab3 PRIVATE /utf-8 /W4)
else()
    target_compile_options(kisb_lab3 PRIVATE -Wall -Wextra)
endif()
