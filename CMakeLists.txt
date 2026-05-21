cmake_minimum_required(VERSION 3.20)
project(oresat_lost_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(CAIRO REQUIRED cairo)

set(PYBIND11_FINDPYTHON ON)
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

# collect data
file(
  GLOB_RECURSE PACKAGE_DATA
  "${CMAKE_SOURCE_DIR}/oresat_star_tracker/*.html"
  "${CMAKE_SOURCE_DIR}/oresat_star_tracker/*.png"
)

foreach(DATA_FILE ${PACKAGE_DATA})
  file(RELATIVE_PATH REL_PATH "${CMAKE_SOURCE_DIR}/oresat_star_tracker/" "${DATA_FILE}")
  get_filename_component(REL_DIR "${REL_PATH}" DIRECTORY)
  install(FILES ${DATA_FILE}
          DESTINATION "${Python_SITELIB}/oresat_star_tracker/${REL_DIR}")
endforeach()

install(FILES "${CMAKE_SOURCE_DIR}/oresat_star_tracker/data/bright-star-catalog.tsv"
        DESTINATION "${Python_SITELIB}/oresat_star_tracker/data")

install(FILES "${CMAKE_SOURCE_DIR}/oresat_star_tracker/data/py-database.dat"
        DESTINATION "${Python_SITELIB}/oresat_star_tracker/data")

set(LOST_SRC_DIR "${CMAKE_SOURCE_DIR}/third_party/lost/src")
set(LOST_VENDOR_DIR "${CMAKE_SOURCE_DIR}/third_party/lost/vendor")

file(
  GLOB LOST_SOURCES
  CONFIGURE_DEPENDS
  "${LOST_SRC_DIR}/*.cpp")
list(FILTER LOST_SOURCES EXCLUDE REGEX ".*/main\\.cpp$")

add_library(lost_objects OBJECT ${LOST_SOURCES})
set_target_properties(lost_objects PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_include_directories(
  lost_objects
  PUBLIC "${LOST_SRC_DIR}" "${LOST_VENDOR_DIR}")
target_compile_options(lost_objects PUBLIC ${CAIRO_CFLAGS_OTHER})
target_include_directories(lost_objects PUBLIC ${CAIRO_INCLUDE_DIRS})

set(ORESAT_LOST_DB
    "${Python_SITELIB}/oresat_star_tracker/data/py-database.dat")
set(ORESAT_LOST_BSC
    "${Python_SITELIB}/oresat_star_tracker/data/bright-star-catalog.tsv")

pybind11_add_module(_lost_core MODULE native/bindings.cpp $<TARGET_OBJECTS:lost_objects>)
target_include_directories(_lost_core PRIVATE "${LOST_SRC_DIR}" "${LOST_VENDOR_DIR}")
target_compile_definitions(
  _lost_core
  PRIVATE "LOST_DB_PATH=\"${ORESAT_LOST_DB}\""
          "LOST_BSC_PATH=\"${ORESAT_LOST_BSC}\"")
target_link_libraries(_lost_core PRIVATE ${CAIRO_LIBRARIES})
target_link_options(_lost_core PRIVATE ${CAIRO_LDFLAGS_OTHER})

install(TARGETS _lost_core LIBRARY DESTINATION oresat_star_tracker)
