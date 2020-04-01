#!/bin/bash

# Set the package name
PKG_NAME="oresat-star-tracker"

# Remove old build directory
OLD=$PKG_NAME"*"
rm -rf $OLD

# Get version and architecture from control file
VERSION=`grep -i version ./config/debfiles/control | cut -d ":" -f 2 | sed 's/ //g'`
ARCHITECTURE=`grep -i architecture ./config/debfiles/control | cut -d ":" -f 2 | sed 's/ //g'`

# Create the build dir
BUILD_DIR=$PKG_NAME"_"$VERSION"_"$ARCHITECTURE
mkdir $BUILD_DIR

# Create and fill the DEBIAN dir
DEBIAN_DIR=$BUILD_DIR"/DEBIAN/"
mkdir $DEBIAN_DIR
cp ./config/debfiles/* $DEBIAN_DIR

# Create debian binary
echo "2.0" > $BUILD_DIR"/debian-binary"

# Documentation
DOC_PATH=$BUILD_DIR"/usr/share/doc/"$PKG_NAME
mkdir -p $DOC_PATH
cp ./LICENSE $DOC_PATH
cp ./README.md $DOC_PATH

# Configuration files, data, and source code
SOURCE_PATH=$BUILD_DIR"/usr/share/"$PKG_NAME
mkdir -p $SOURCE_PATH
cp -r ./config $SOURCE_PATH
cp -r ./data $SOURCE_PATH
cp -r ./src $SOURCE_PATH

#make md5sums file
cd $BUILD_DIR
find . -type f ! -regex '.*?debian-binary.*' ! -regex '.*?DEBIAN.*' -printf '%P ' | xargs md5sum > DEBIAN/md5sums
cd -

dpkg -b $BUILD_DIR"/"