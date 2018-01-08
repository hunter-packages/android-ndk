#!/usr/bin/env python3

import argparse
import hashlib
import os
import platform
import requests
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import zipfile

def get_directory_size(dir_path):
  total_size = 0
  for dirpath, dirnames, filenames in os.walk(dir_path):
    for f in filenames:
      fp = os.path.join(dirpath, f)
      if not os.path.islink(fp):
        total_size += os.path.getsize(fp)
  return total_size

def get_object_size(obj_path):
  if os.path.isfile(obj_path):
    return os.path.getsize(obj_path)
  else:
    return get_directory_size(obj_path)

def human_readable_size(size):
  kb = 1024
  mb = 1024 * kb
  gb = 1024 * mb
  if size < kb:
    return size, 'B'
  if size < mb:
    return size / kb, 'KB'
  if size < gb:
    return size / mb, 'MB'
  return size / gb, 'GB'

def object_printable_size(obj_path):
  size, suffix = human_readable_size(get_object_size(obj_path))
  return '{:.2f} {}'.format(size, suffix)

class FileToDownload:
  def __init__(self, url, sha1, local_path, unpack_dir):
    self.url = url
    self.sha1 = sha1
    self.local_path = local_path
    self.unpack_dir = unpack_dir

    self.download()
    self.unpack()

  def download(self):
    ok = self.hash_match()
    if ok:
      print('File already downloaded: {}'.format(self.local_path))
    else:
      self.real_file_download()
      assert(self.hash_match() == True)

  def hash_match(self):
    if not os.path.exists(self.local_path):
      print('File not exists: {}'.format(self.local_path))
      return False
    print('Calculating hash of {}'.format(self.local_path))
    sha1_of_file = hashlib.sha1(open(self.local_path, 'rb').read()).hexdigest()
    ok = (sha1_of_file == self.sha1)
    if ok:
      return True
    else:
      print('SHA1 mismatch for file {}:'.format(self.local_path))
      print('  {} (real)'.format(sha1_of_file))
      print('  {} (expected)'.format(self.sha1))
      return False

  def real_file_download(self):
    max_retry = 3
    for i in range(max_retry):
      try:
        self.real_file_download_once()
        print('Done')
        return
      except Exception as exc:
        print('Exception catched ({}), retry... ({} of {})'.format(exc, i+1, max_retry))
        time.sleep(60)
    sys.exit('Download failed')

  # http://stackoverflow.com/a/16696317/2288008
  def real_file_download_once(self):
    print('Downloading:\n  {}\n  -> {}'.format(self.url, self.local_path))
    r = requests.get(self.url, stream=True)
    if not r.ok:
      raise Exception('Downloading failed: {}'.format(self.url))
    with open(self.local_path, 'wb') as f:
      for chunk in r.iter_content(chunk_size=16*1024):
        if chunk:
          f.write(chunk)

  def unpack(self):
    print('Unpacking {}'.format(self.local_path))
    # Change directory for '.zip' and '.bin' cases
    last_cwd = os.getcwd()
    os.chdir(self.unpack_dir)
    if self.url.endswith('.tar.gz'):
      tar_archive = tarfile.open(self.local_path)
      tar_archive.extractall(path=self.unpack_dir)
      tar_archive.close()
    elif self.url.endswith('.zip'):
      # Can't use ZipFile module because permissions will be lost, see bug:
      # * https://bugs.python.org/issue15795
      subprocess.check_call(['unzip', self.local_path])
    elif self.url.endswith('.bin'):
      os.chmod(self.local_path, os.stat(self.local_path).st_mode | stat.S_IEXEC)
      devnull = open(os.devnull, 'w') # subprocess.DEVNULL is not available for Python 3.2
      subprocess.check_call(android_archive_local, stdout=devnull)
    else:
      sys.exit('Unknown archive format')
    os.chdir(last_cwd)

def stl_suffix_by_name(stl_name):
  if stl_name == 'system' or stl_name == 'system_re':
    return 'system'
  if stl_name == 'gabi++_shared' or stl_name == 'gabi++_static':
    return 'gabi++'
  if stl_name == 'stlport_shared' or stl_name == 'stlport_static':
    return 'stlport'
  if stl_name == 'gnustl_shared' or stl_name == 'gnustl_static':
    return 'gnu-libstdc++'
  if stl_name == 'c++_static' or stl_name == 'c++_shared':
    return 'llvm-libc++'
  sys.exit('Unexpected --stl: {}'.format(stl_name))

parser = argparse.ArgumentParser(
    description='Create minimal Android NDK'
)

parser.add_argument('--toolchain', help="Toolchain name")
parser.add_argument('--stl', help="STL name")
parser.add_argument('--compiler-version', help="Compiler version")
parser.add_argument('--abi-name', help="ABI name")
parser.add_argument('--api-level', help="API level")
parser.add_argument('--arch-name', help="Architecture name")

parser.add_argument(
    '--ndk-version', choices=['r10e', 'r11c', 'r15c', 'r16b'], help="NDK version"
)

args = parser.parse_args()

if not args.toolchain:
  sys.exit('--toolchain is required')

if not args.stl:
  sys.exit('--stl is required')

if not args.api_level:
  sys.exit('--api-level is required')

if not args.arch_name:
  sys.exit('--arch-name is required')

top_dir = os.getcwd()

downloads_dir = os.path.join(top_dir, '_downloads')
unpack_dir = os.path.join(top_dir, '_unpacked')
pruned_dir = os.path.join(top_dir, '_pruned')

if not os.path.exists(downloads_dir):
  print('Creating new directory: {}'.format(downloads_dir))
  os.mkdir(downloads_dir)

if os.path.exists(unpack_dir):
  print('Cleanup directory: {}'.format(unpack_dir))
  shutil.rmtree(unpack_dir)
os.mkdir(unpack_dir)

if not os.path.exists(pruned_dir):
  os.mkdir(pruned_dir)

ndk_version = args.ndk_version

if ndk_version == 'r10e':
  archive_suffix = 'bin'
else:
  archive_suffix = 'zip'

android_archive_local = os.path.join(downloads_dir, 'android-ndk-{}.{}'.format(ndk_version, archive_suffix))
android_unpacked_ndk = os.path.join(unpack_dir, 'android-ndk-{}'.format(ndk_version))
android_toolchains_dir = os.path.join(android_unpacked_ndk, 'toolchains')
android_stl_dir = os.path.join(android_unpacked_ndk, 'sources', 'cxx-stl')
android_platforms_dir = os.path.join(android_unpacked_ndk, 'platforms')

android_pruned_name = 'android-ndk-{}'.format(ndk_version)

# http://developer.android.com/ndk/downloads/index.html
def get_darwin_info():
  if ndk_version == 'r10e':
    return (
        'http://dl.google.com/android/ndk/android-ndk-r10e-darwin-x86_64.bin',
        'b57c2b9213251180dcab794352bfc9a241bf2557'
    )
  if ndk_version == 'r11c':
    return (
        'http://dl.google.com/android/repository/android-ndk-r11c-darwin-x86_64.zip',
        '4ce8e7ed8dfe08c5fe58aedf7f46be2a97564696'
    )
  if ndk_version == 'r15c':
    return (
        'https://dl.google.com/android/repository/android-ndk-r15c-darwin-x86_64.zip',
        'ea4b5d76475db84745aa8828000d009625fc1f98'
    )
  sys.exit('Unknown NDK version')

def get_linux_info():
  if ndk_version == 'r10e':
    return (
        'http://dl.google.com/android/ndk/android-ndk-r10e-linux-x86_64.bin',
        'c685e5f106f8daa9b5449d0a4f21ee8c0afcb2f6'
    )
  if ndk_version == 'r11c':
    return (
        'http://dl.google.com/android/repository/android-ndk-r11c-linux-x86_64.zip',
        'de5ce9bddeee16fb6af2b9117e9566352aa7e279'
    )
  if ndk_version == 'r15c':
    return (
        'https://dl.google.com/android/repository/android-ndk-r15c-linux-x86_64.zip',
        '0bf02d4e8b85fd770fd7b9b2cdec57f9441f27a2'
    )
  if ndk_version == 'r16b':
    return (
        'https://dl.google.com/android/repository/android-ndk-r16b-linux-x86_64.zip',
        '42aa43aae89a50d1c66c3f9fdecd676936da6128'
    )
  sys.exit('Unknown NDK version')

if platform.system() == 'Darwin':
  url, sha1 = get_darwin_info()
  FileToDownload(url, sha1, android_archive_local, unpack_dir)
elif platform.system() == 'Linux':
  url, sha1 = get_linux_info()
  FileToDownload(url, sha1, android_archive_local, unpack_dir)
else:
  sys.exit('Android supported only for Linux and OSX')

original_info = 'Original sizes: archive {}, unpacked {}'.format(
    object_printable_size(android_archive_local),
    object_printable_size(android_unpacked_ndk)
)

toolchain = args.toolchain
if args.compiler_version == 'clang':
  toolchain = toolchain.replace('-clang', '-4.9')

toolchain_dir = os.path.join(android_toolchains_dir, toolchain)

if not os.path.exists(toolchain_dir):
  print('Toolchain not exists: {} (set by --toolchain)'.format(toolchain_dir))

toolchains_list = os.listdir(android_toolchains_dir)
if not toolchain in toolchains_list:
  sys.exit('Toolchain `{}` is not in list: {}'.format(toolchain, toolchains_list))

stl_suffix = stl_suffix_by_name(args.stl)

stl_dir = os.path.join(android_stl_dir, stl_suffix)
if not os.path.exists(stl_dir):
  print('STL not exists: {} (set by --stl)'.format(stl_dir))

stl_list = os.listdir(android_stl_dir)
if not stl_suffix in stl_list:
  sys.exit('STL `{}` is not in list: {}'.format(stl_suffix, stl_list))

print('Removing unused toolchains:')
toolchain_found = False
for x in toolchains_list:
  set_toolchain_found = (x == toolchain)
  remove_dir = not set_toolchain_found
  if (args.compiler_version == 'clang') and (x == 'llvm'):
    remove_dir = False

  if remove_dir:
    toremove = os.path.join(android_toolchains_dir, x)
    print('  - {}'.format(toremove))
    shutil.rmtree(toremove)

  if set_toolchain_found:
    if toolchain_found:
      sys.exit('Already found')
    else:
      toolchain_found = True

if not toolchain_found:
  sys.exit('Toolchain not found')

android_pruned_name = '{}-{}'.format(android_pruned_name, toolchain)

print('Removing unused STL:')
stl_found = False
for x in stl_list:
  set_stl_found = (x == stl_suffix)
  remove_dir = not set_stl_found
  if (stl_suffix == 'llvm-libc++') and (x == 'llvm-libc++abi'):
    remove_dir = False

  if remove_dir:
    toremove = os.path.join(android_stl_dir, x)
    print('  - {}'.format(toremove))
    shutil.rmtree(toremove)

  if set_stl_found:
    if stl_found:
      sys.exit('Already found')
    else:
      stl_found = True

if not stl_found:
  sys.exit('STL not found')

android_pruned_name = '{}-{}'.format(android_pruned_name, stl_suffix)

if stl_suffix == 'gnu-libstdc++':
  gcc_version = args.compiler_version
  if not gcc_version:
    sys.exit('Expected --compiler-version')
  gcc_version_dir = os.path.join(stl_dir, gcc_version)
  if not os.path.exists(gcc_version_dir):
    sys.exit('Directory not exists: {} (--compiler-version)'.format(gcc_version_dir))
  versions_list = os.listdir(stl_dir)
  if not gcc_version in versions_list:
    sys.exit('{} not found in {}'.format(gcc_version, versions_list))
  print('Removing unused compilers versions:')
  found = False
  for x in versions_list:
    x_path = os.path.join(stl_dir, x)
    if x == gcc_version:
      if found:
        sys.exit('Already found')
      else:
        found = True
      continue
    if not os.path.isdir(x_path):
      continue
    print('  - {}'.format(x_path))
    shutil.rmtree(x_path)
  if not found:
    sys.exit('Not found')

  android_pruned_name = '{}-{}'.format(android_pruned_name, gcc_version)

  if not args.abi_name:
    sys.exit('Expected --abi-name')
  libs_dir = os.path.join(gcc_version_dir, 'libs')
  abi_dir = os.path.join(libs_dir, args.abi_name)
  if not os.path.exists(abi_dir):
    sys.exit('Directory not exists: {} (--abi-name)'.format(abi_dir))
  abi_list = os.listdir(libs_dir)
  if not args.abi_name in abi_list:
    sys.exit('{} not found in {}'.format(args.abi_name, abi_list))
  found = False
  print('Removing unused ABI:')
  for x in abi_list:
    if x == args.abi_name:
      if found:
        sys.exit('Already found')
      else:
        found = True
      continue
    toremove = os.path.join(libs_dir, x)
    print('  - {}'.format(toremove))
    shutil.rmtree(toremove)
  if not found:
    sys.exit('Not found')
  android_pruned_name = '{}-{}'.format(android_pruned_name, args.abi_name)

android_api = 'android-{}'.format(args.api_level)
android_api_dir = os.path.join(android_platforms_dir, android_api)
if not os.path.exists(android_api_dir):
  sys.exit('Directory not found: {} (--api-level)'.format(android_api_dir))
api_list = os.listdir(android_platforms_dir)
if not android_api in api_list:
  sys.exit('{} not found in {}'.format(android_api, api_list))
found = False
print('Removing unused API:')
for x in api_list:
  toremove = os.path.join(android_platforms_dir, x)
  if not os.path.isdir(toremove):
    continue
  if x == android_api:
    if found:
      sys.exit('Already found')
    else:
      found = True
    continue
  print('  - {}'.format(toremove))
  shutil.rmtree(toremove)
if not found:
  sys.exit('API not found')

android_pruned_name = '{}-{}'.format(android_pruned_name, android_api)

android_arch = 'arch-{}'.format(args.arch_name)
android_arch_dir = os.path.join(android_api_dir, android_arch)
if not os.path.exists(android_arch_dir):
  sys.exit('Directory not found: {} (--arch-name)'.format(android_arch_dir))

arch_list = os.listdir(android_api_dir)
if not android_arch in arch_list:
  sys.exit('{} not found in {}'.format(android_arch, arch_list))

found = False
print('Removing unused architectures:')
for x in arch_list:
  if x == android_arch:
    if found:
      sys.exit('Already found')
    found = True
    continue
  toremove = os.path.join(android_api_dir, x)
  print('  - {}'.format(toremove))
  if os.path.isdir(toremove):
    shutil.rmtree(toremove)
  else:
    os.remove(toremove)
if not found:
  sys.exit('Not found')

android_pruned_name = '{}-{}'.format(android_pruned_name, android_arch)
android_pruned_name = '{}-{}'.format(android_pruned_name, platform.system())
android_pruned_name = '{}.tar.gz'.format(android_pruned_name)

android_pruned_archive = os.path.join(pruned_dir, android_pruned_name)

print('Creating archive')

arch = tarfile.open(android_pruned_archive, 'w:gz')
arch.add(android_unpacked_ndk, arcname='android-ndk-{}'.format(ndk_version))
arch.close()

pruned_info = 'Pruned sizes: archive {}, unpacked {}'.format(
    object_printable_size(android_pruned_archive),
    object_printable_size(android_unpacked_ndk)
)

print(original_info)
print(pruned_info)

print('Pruned archive ready: {}'.format(android_pruned_archive))
