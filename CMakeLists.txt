cmake_minimum_required(VERSION 3.18 FATAL_ERROR)
set(PROJECT_VERSION_MAJOR 1)
set(PROJECT_VERSION_MINOR 0)
set(PROJECT_VERSION_PATCH 0)
set(PROJECT_VERSION ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}.${PROJECT_VERSION_PATCH})
set(CMAKE_CXX_STANDARD 17)

project(GameAnywhere VERSION ${PROJECT_VERSION} LANGUAGES C CXX)

if ( ${CMAKE_SOURCE_DIR} STREQUAL ${CMAKE_BINARY_DIR} )
    message( FATAL_ERROR "In-source builds not allowed! Create a build directory and run CMake from there." )
endif()

set(SanitizeType "None" CACHE STRING "What sanitizers to use")
set_property(CACHE SanitizeType PROPERTY STRINGS "None" "adress" "thread" "undefined" "leak" "memory")

set(DEFAULT_BUILD_TYPE "Debug")

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    message(STATUS "Setting build type to '${DEFAULT_BUILD_TYPE}' as none was specified.")
    set(CMAKE_BUILD_TYPE "${DEFAULT_BUILD_TYPE}" CACHE STRING "Choose the type of build." FORCE)
    # Set the possible values of build type for cmake-gui
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release" "MinSizeRel" "RelWithDebInfo")
endif()


set(c_flags
    -Wall -Wextra -Werror
    -Wcast-align -Wunused -Wpedantic
    -Wdouble-promotion
    -Wformat=2
)
set(cxx_flags
    -Woverloaded-virtual -Wnon-virtual-dtor
)
set(gcc_flags
    -Wmisleading-indentation
    -Wduplicated-cond
    -Wlogical-op
)
set(gcc_cxx_flags -Wuseless-cast)
add_compile_options(
    "$<$<COMPILE_LANGUAGE:CXX>:${cxx_flags}>"
    "$<$<CXX_COMPILER_ID:GNU>:${gcc_flags}>"
    "$<$<AND:$<COMPILE_LANGUAGE:CXX>,$<CXX_COMPILER_ID:GNU>>:${gcc_cxx_flags}>"
)

set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17")

include_directories(include)
add_subdirectory(src)
add_subdirectory(examples)

set(CONFIGURED_ONCE TRUE CACHE INTERNAL
        "A flag showing that CMake has configured at least once.")
