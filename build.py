#!/usr/bin/env python
#
# Copyright © 2022 Github Lzhiyong
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# pylint: disable=not-callable, line-too-long, no-else-return

import os
import re
import time
import shutil
import argparse
import subprocess
import zipfile
from pathlib import Path

def format_time(seconds):
    minute, sec = divmod(seconds, 60)
    hour, minute = divmod(minute, 60)
    
    hour = int(hour)
    minute = int(minute)
    if minute < 1:
        sec = float('%.2f' % sec)
    else:
        sec = int(sec)

    if hour != 0:
        return '{}h{}m{}s'.format(hour, minute, sec)
    elif minute != 0:
        return '{}m{}s'.format(minute, sec)
    else:
        return '{}s'.format(sec)

# package a directory as zip file
def package(srcPathName, destPathName):
    zip = zipfile.ZipFile(destPathName, 'w', zipfile.ZIP_DEFLATED)
    for path, dirs, names in os.walk(srcPathName):
        fpath = path.replace(srcPathName, '')
        for filename in names:
            zip.write(os.path.join(path, filename), os.path.join(fpath, filename))            
    zip.close()

# generate package.xml for build-tools
def gen_build_tools_package_xml(version):
    parts = version.split('.')
    major = parts[0] if len(parts) > 0 else '0'
    minor = parts[1] if len(parts) > 1 else '0'
    micro = parts[2] if len(parts) > 2 else '0'

    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:repository
    xmlns:ns2="http://schemas.android.com/repository/android/common/02"
    xmlns:ns3="http://schemas.android.com/repository/android/common/01"
    xmlns:ns4="http://schemas.android.com/repository/android/generic/01"
    xmlns:ns5="http://schemas.android.com/repository/android/generic/02"
    xmlns:ns6="http://schemas.android.com/sdk/android/repo/addon2/01"
    xmlns:ns7="http://schemas.android.com/sdk/android/repo/addon2/02"
    xmlns:ns8="http://schemas.android.com/sdk/android/repo/repository2/01"
    xmlns:ns9="http://schemas.android.com/sdk/android/repo/repository2/02"
    xmlns:ns10="http://schemas.android.com/sdk/android/repo/sys-img2/02"
    xmlns:ns11="http://schemas.android.com/sdk/android/repo/sys-img2/01">
    <license id="android-sdk-license" type="text">Terms and Conditions</license>
    <localPackage path="build-tools;{version}" obsolete="false">
        <type-details xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="ns5:genericDetailsType"/>
        <revision>
            <major>{major}</major>
            <minor>{minor}</minor>
            <micro>{micro}</micro>
        </revision>
        <display-name>Android SDK Build-Tools {version}</display-name>
        <uses-license ref="android-sdk-license"/>
    </localPackage>
</ns2:repository>'''.format(version=version, major=major, minor=minor, micro=micro)

# generate package.xml for platform-tools
def gen_platform_tools_package_xml(version):
    parts = version.split('.')
    major = parts[0] if len(parts) > 0 else '0'
    minor = parts[1] if len(parts) > 1 else '0'
    micro = parts[2] if len(parts) > 2 else '0'

    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:repository
    xmlns:ns2="http://schemas.android.com/repository/android/common/02"
    xmlns:ns3="http://schemas.android.com/repository/android/common/01"
    xmlns:ns4="http://schemas.android.com/repository/android/generic/01"
    xmlns:ns5="http://schemas.android.com/repository/android/generic/02"
    xmlns:ns6="http://schemas.android.com/sdk/android/repo/addon2/01"
    xmlns:ns7="http://schemas.android.com/sdk/android/repo/addon2/02"
    xmlns:ns8="http://schemas.android.com/sdk/android/repo/repository2/01"
    xmlns:ns9="http://schemas.android.com/sdk/android/repo/repository2/02"
    xmlns:ns10="http://schemas.android.com/sdk/android/repo/sys-img2/02"
    xmlns:ns11="http://schemas.android.com/sdk/android/repo/sys-img2/01">
    <license id="android-sdk-license" type="text">Terms and Conditions</license>
    <localPackage path="platform-tools" obsolete="false">
        <type-details xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="ns5:genericDetailsType"/>
        <revision>
            <major>{major}</major>
            <minor>{minor}</minor>
            <micro>{micro}</micro>
        </revision>
        <display-name>Android SDK Platform-Tools</display-name>
        <uses-license ref="android-sdk-license"/>
    </localPackage>
</ns2:repository>'''.format(version=version, major=major, minor=minor, micro=micro)

# generate source.properties
def gen_source_properties(desc, revision, pkg_path):
    return 'Pkg.Desc = {}\nPkg.Revision = {}\nPkg.Path = {}\nPkg.UserSrc = false\n'.format(
        desc, revision, pkg_path)

# parse SDK version from tag like "platform-tools-35.0.2" -> "35.0.2"
def parse_version(tag):
    if not tag:
        return '35.0.0'
    match = re.search(r'(\d+\.\d+\.\d+)', tag)
    if match:
        return match.group(1)
    return '35.0.0'

# build finish
def complete(args):
    sdk_version = parse_version(args.tag)
    binary_dir = Path.cwd() / args.build / 'bin'
    staging_dir = Path.cwd() / args.build / 'staging'

    # arch maps
    arch = {
        'arm64-v8a': 'aarch64',
        'armeabi-v7a': 'arm',
        'x86_64': 'x86_64',
        'x86': 'i686'
    }

    # ndk llvm-strip
    strip = Path(args.ndk) / 'toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip'

    # the android tools list
    build_tools_bin = ['aapt', 'aapt2', 'aidl', 'zipalign', 'dexdump', 'split-select']
    platform_tools_bin = [
        'adb', 'fastboot', 'sqlite3', 'etc1tool', 'hprof-conv',
        'e2fsdroid', 'sload_f2fs', 'mke2fs', 'make_f2fs', 'make_f2fs_casefold'
    ]
    other_tools = ['veridex']

    # staging directory structure
    build_tools_dir = staging_dir / 'build-tools' / sdk_version
    platform_tools_dir = staging_dir / 'platform-tools'
    others_dir = staging_dir / 'others'

    for d in [build_tools_dir, platform_tools_dir, others_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # copy and strip build-tools
    for tool in build_tools_bin:
        src = binary_dir / tool
        if src.exists():
            dst = build_tools_dir / tool
            shutil.copy2(src, dst)
            os.remove(src)
            subprocess.run('{} -g {}'.format(strip, dst), shell=True)

    # copy and strip platform-tools
    for tool in platform_tools_bin:
        src = binary_dir / tool
        if src.exists():
            dst = platform_tools_dir / tool
            shutil.copy2(src, dst)
            os.remove(src)
            subprocess.run('{} -g {}'.format(strip, dst), shell=True)

    # copy and strip others
    for tool in other_tools:
        src = binary_dir / tool
        if src.exists():
            dst = others_dir / tool
            shutil.copy2(src, dst)
            os.remove(src)
            subprocess.run('{} -g {}'.format(strip, dst), shell=True)

    # write package.xml and source.properties for build-tools
    (build_tools_dir / 'package.xml').write_text(gen_build_tools_package_xml(sdk_version))
    (build_tools_dir / 'source.properties').write_text(
        gen_source_properties('Android SDK Build-Tools {}'.format(sdk_version), sdk_version,
                              'build-tools;{}'.format(sdk_version)))

    # write package.xml and source.properties for platform-tools
    (platform_tools_dir / 'package.xml').write_text(gen_platform_tools_package_xml(sdk_version))
    (platform_tools_dir / 'source.properties').write_text(
        gen_source_properties('Android SDK Platform-Tools', sdk_version, 'platform-tools'))

    # package as AndroidSDK-VERSION.zip
    zip_name = 'AndroidSDK-{}.zip'.format(sdk_version)
    zip_path = Path.cwd() / zip_name
    package(str(staging_dir), str(zip_path))
    print('\033[1;32mpackaged to {}\033[0m'.format(zip_path))
    
# start building
def build(args):
    ndk = Path(args.ndk)
    cmake_toolchain_file = ndk / 'build/cmake/android.toolchain.cmake'
    if not cmake_toolchain_file.exists():
        raise ValueError('no such file or directory: {}'.format(cmake_toolchain_file))
        
    command = ['cmake', '-GNinja',
        '-B {}'.format(args.build),
        '-DANDROID_NDK={}'.format(args.ndk),
        '-DCMAKE_TOOLCHAIN_FILE={}'.format(cmake_toolchain_file),
        '-DANDROID_PLATFORM=android-{}'.format(args.api),
        '-DCMAKE_ANDROID_ARCH_ABI={}'.format(args.abi),
        '-DANDROID_ABI={}'.format(args.abi),
        '-DCMAKE_SYSTEM_NAME=Android',
        '-Dprotobuf_BUILD_TESTS=OFF',
        '-DABSL_PROPAGATE_CXX_STD=ON',
        '-DANDROID_ARM_NEON=ON',
        '-DCMAKE_BUILD_TYPE=Release',
        '-DCMAKE_POLICY_VERSION_MINIMUM=3.5']
    
    if args.protoc is not None:
        if not Path(args.protoc).exists():
            raise ValueError('no such file or directory: {}'.format(args.protoc))
        command.append('-DPROTOC_PATH={}'.format(args.protoc))
    
    result = subprocess.run(command)
    start_time = time.time()
    if result.returncode == 0:
        if args.target == 'all':
            result = subprocess.run(['ninja', '-C', args.build, '-j {}'.format(args.job)])
        else:
            result = subprocess.run(['ninja', '-C', args.build, args.target, '-j {}'.format(args.job)])

    if result.returncode == 0:
        # build finish
        complete(args)
        end_time = time.time()
        print('\033[1;32mbuild success cost time: {}\033[0m'.format(format_time(end_time - start_time)))
  
def main():
    parser = argparse.ArgumentParser()
    tasks = os.cpu_count()

    parser.add_argument('--ndk', required=True, help='set the ndk toolchain path')

    parser.add_argument('--abi', choices=['armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64'], 
      required=True, help='build for the specified architecture')
    
    parser.add_argument('--api', default=30, help='set android platform level, min api is 30')

    parser.add_argument('--build', default='build', help='the build directory')

    parser.add_argument('--job', default=tasks, help='run N jobs in parallel, default is {}'.format(tasks))
    
    parser.add_argument('--target', default='all', help='build specified targets such as aapt2 adb fastboot, etc')
    
    parser.add_argument('--protoc', help='set the host protoc path')
    parser.add_argument('--tag', default='master', help='SDK version tag for packaging (e.g., platform-tools-35.0.2)')

    args = parser.parse_args()

    build(args)

if __name__ == '__main__':
    main()

