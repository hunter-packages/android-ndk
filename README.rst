Script for creating minimalized archives with Android NDK for faster CI testing.

Usage
-----

First you need to extract internal CMake variables from Android toolchain. To do it run configure for top
level ``CMakeLists.txt``:

.. code-block:: shell

  > build.py --toolchain android-ndk-r10e-api-19-armeabi-v7a-neon --verbose --clear --nobuild

Next variables will be printed::

  ANDROID_TOOLCHAIN_NAME: arm-linux-androideabi-4.9
  ANDROID_STL: gnustl_static
  ANDROID_COMPILER_VERSION: 4.9
  ANDROID_NDK_ABI_NAME: armeabi-v7a
  ANDROID_NATIVE_API_LEVEL: 19
  ANDROID_ARCH_NAME: arm

And command to run::

  Run:
    ./create-android-ndk.py --toolchain arm-linux-androideabi-4.9 --stl gnustl_static --compiler-version 4.9 --abi-name armeabi-v7a --api-level 19 --arch-name arm

Run it! Statistic and final archive name will be printed at the end::

  Original sizes: archive 382.92 MB, unpacked 2.88 GB
  Pruned sizes: archive 96.75 MB, unpacked 291.24 MB
  Pruned archive ready: /.../_pruned/android-ndk-r10e-arm-linux-androideabi-4.9-gnu-libstdc++-4.9-armeabi-v7a-android-19-arch-arm-Linux.tar.gz
