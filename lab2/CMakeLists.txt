cmake_minimum_required(VERSION 3.16)
project(kisb_lab2 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(kisb_lab2 src/main.cpp)

if(MSVC)
  target_compile_options(kisb_lab2 PRIVATE /W4 /utf-8)
else()
  target_compile_options(kisb_lab2 PRIVATE -Wall -Wextra -O2)
endif()
