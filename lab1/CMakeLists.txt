cmake_minimum_required(VERSION 3.10)

project(Lab1_Variant2 VERSION 1.0 DESCRIPTION "Variant 2 of lab work #1")

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2")

add_executable(variant2
    main.cpp
    lfsr.cpp
    sg_generator.cpp
    prime_utils.cpp
)

target_include_directories(variant2 PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})