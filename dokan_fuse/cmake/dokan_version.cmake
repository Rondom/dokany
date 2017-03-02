file(READ "${CMAKE_CURRENT_SOURCE_DIR}/../dokan_version.txt" DOKAN_BASE_VERSION)

if(NOT DOKAN_BUILD_NUMER)
    set(DOKAN_BUILD_NUMBER "0")
endif()

string(REGEX MATCH "^([0-9]+)\\.([0-9]+)\\.([0-9]+)\\.([0-9]+)"
       DOKAN_BASE_VERSION ${DOKAN_BASE_VERSION})

set(dokan_version_major ${CMAKE_MATCH_1})
set(dokan_version_minor ${CMAKE_MATCH_2})
set(dokan_version_minor_minor ${CMAKE_MATCH_3})
math(EXPR dokan_version_patch "${CMAKE_MATCH_4} + ${DOKAN_BUILD_NUMBER}")

set(dokan_version_dot
    "${dokan_version_major}.${dokan_version_minor}.${dokan_version_minor_minor}.${dokan_version_patch}")
set(dokan_version_comma
    "${dokan_version_major},${dokan_version_minor},${dokan_version_minor_minor},${dokan_version_patch}")
set(dokan_api_version "${dokan_version_major}")

add_definitions("-DDOKAN_BUILD_VERSION_DOT=${dokan_version_dot}")
add_definitions("-DDOKAN_BUILD_VERSION_COMMA=${dokan_version_comma}")
add_definitions("-DDOKAN_BUILD_MAJOR_API_VERSION=${dokan_api_version}")
