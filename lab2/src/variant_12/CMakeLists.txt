cmake_minimum_required(VERSION 3.20)
project(kisb_lab2_variant12 LANGUAGES CXX)

add_executable(kisb_lab2_variant12 main.cpp)
target_compile_features(kisb_lab2_variant12 PRIVATE cxx_std_17)
target_compile_options(kisb_lab2_variant12 PRIVATE -Wall -Wextra -Wpedantic)

configure_file(message.txt message.txt COPYONLY)
