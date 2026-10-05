cmake_minimum_required(VERSION 3.20)
project(kisb_lab1_variant12 LANGUAGES CXX)

add_executable(kisb_lab1_variant12 main.cpp)
target_compile_features(kisb_lab1_variant12 PRIVATE cxx_std_17)
target_compile_options(kisb_lab1_variant12 PRIVATE -Wall -Wextra -Wpedantic)
