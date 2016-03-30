cmake_minimum_required(VERSION 3.0)
project(ShowSettings)

set(cmd "  ./create-android-ndk.py")

set(cmd "${cmd} --toolchain ${ANDROID_TOOLCHAIN_NAME}")
set(cmd "${cmd} --stl ${ANDROID_STL}")
set(cmd "${cmd} --compiler-version ${ANDROID_COMPILER_VERSION}")
set(cmd "${cmd} --abi-name ${ANDROID_NDK_ABI_NAME}")
set(cmd "${cmd} --api-level ${ANDROID_NATIVE_API_LEVEL}")
set(cmd "${cmd} --arch-name ${ANDROID_ARCH_NAME}")

message("Run:")
message("${cmd}")
