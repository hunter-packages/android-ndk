cmake_minimum_required(VERSION 3.0)
project(ShowSettings)

message("ANDROID_NDK_VERSION: ${ANDROID_NDK_VERSION}")
message("ANDROID_TOOLCHAIN_NAME: ${ANDROID_TOOLCHAIN_NAME}")
message("ANDROID_STL: ${ANDROID_STL}")
message("ANDROID_COMPILER_VERSION: ${ANDROID_COMPILER_VERSION}")
message("ANDROID_NDK_ABI_NAME: ${ANDROID_NDK_ABI_NAME}")
message("ANDROID_NATIVE_API_LEVEL: ${ANDROID_NATIVE_API_LEVEL}")
message("ANDROID_ARCH_NAME: ${ANDROID_ARCH_NAME}")

set(cmd "  ./create-android-ndk.py")

set(cmd "${cmd} --ndk-version ${ANDROID_NDK_VERSION}")
set(cmd "${cmd} --toolchain ${ANDROID_TOOLCHAIN_NAME}")
set(cmd "${cmd} --stl ${ANDROID_STL}")
set(cmd "${cmd} --compiler-version ${ANDROID_COMPILER_VERSION}")
set(cmd "${cmd} --abi-name ${ANDROID_NDK_ABI_NAME}")
set(cmd "${cmd} --api-level ${ANDROID_NATIVE_API_LEVEL}")
set(cmd "${cmd} --arch-name ${ANDROID_ARCH_NAME}")

message("Run:")
message("${cmd}")
