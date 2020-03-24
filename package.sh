#!/bin/bash

# Set the package name
PKG_NAME="oresat-startracker"

# Remove old build directory
OLD=$PKG_NAME"*"
rm -rf $OLD

# Get version and architecture from control file
VERSION=`grep -i version ./debfiles/control | cut -d ":" -f 2 | sed 's/ //g'`
ARCHITECTURE=`grep -i architecture ./debfiles/control | cut -d ":" -f 2 | sed 's/ //g'`

# Create the build dir
BUILD_DIR=$PKG_NAME"_"$VERSION"_"$ARCHITECTURE
mkdir $BUILD_DIR

# Create the DEBIAN dir
DEBIAN_DIR=$BUILD_DIR"/DEBIAN/"
mkdir $DEBIAN_DIR
cp ./debfiles/* $DEBIAN_DIR

# Create debian binary
echo "2.0" > $BUILD_DIR"/debian-binary"

# systemd conf
DBUS_PATH=$BUILD_DIR"/usr/share/dbus-1/system.d/"
mkdir -p $DBUS_PATH
cp ./configs/org.OreSat.StarTracker.conf $DBUS_PATH

# systemd service
DAEMON_PATH=$BUILD_DIR"/lib/systemd/system/"
mkdir -p $DAEMON_PATH
cp ./configs/oresat-startracker.service $DAEMON_PATH

# Documentation
DOC_PATH=$BUILD_DIR"/usr/share/doc/"$PKG_NAME
mkdir -p $DOC_PATH
cp ./LICENSE $DOC_PATH
cp ./README.md $DOC_PATH

# Source code + data
SOURCE_PATH=$BUILD_DIR"/usr/share/"$PKG_NAME
mkdir -p $SOURCE_PATH
cp -r ./beast $SOURCE_PATH
cp -r ./datasets $SOURCE_PATH
cp ./*.py $SOURCE_PATH
cp ./*.dat $SOURCE_PATH
cp ./Makefile $SOURCE_PATH
cp ./run.sh $SOURCE_PATH

#make md5sums file
cd $BUILD_DIR
find . -type f ! -regex '.*?debian-binary.*' ! -regex '.*?DEBIAN.*' -printf '%P ' | xargs md5sum > DEBIAN/md5sums
cd -

dpkg -b $BUILD_DIR"/"