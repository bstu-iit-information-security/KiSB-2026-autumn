cmake_minimum_required(VERSION 3.20)
project(kisb_lab2_variant12 LANGUAGES CXX)

add_executable(kisb_lab2_variant12 main.cpp)
target_compile_features(kisb_lab2_variant12 PRIVATE cxx_std_17)
if(MSVC)
    target_compile_options(kisb_lab2_variant12 PRIVATE /W4 /utf-8)
else()
    target_compile_options(kisb_lab2_variant12 PRIVATE -Wall -Wextra -Wpedantic)
endif()

enable_testing()
add_executable(lab2_tests tests.cpp)
target_compile_features(lab2_tests PRIVATE cxx_std_17)
add_test(NAME error_patterns COMMAND lab2_tests)

configure_file(message.txt message.txt COPYONLY)
