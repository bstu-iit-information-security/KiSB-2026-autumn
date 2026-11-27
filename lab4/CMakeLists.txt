cmake_minimum_required(VERSION 3.10)
project(kisb_lab4 CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options(/utf-8)
endif()

add_executable(kisb_lab4
    src/main.cpp
    src/bignum.cpp
    src/sha512.cpp
    src/curve.cpp
    src/secure.cpp
    src/protocols.cpp)
