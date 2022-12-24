#!/bin/bash
cd $(dirname $(readlink -f $0))/..

PKGNAME=exonutils
VERSION=$(grep '__version__ = "' src/${PKGNAME}/__init__.py \
    |head -n 1 |cut -d'"' -f2 |xargs)

BUILD_VER=${VERSION}
echo "${BUILD_VER}" |grep -q 'dev' && {
    BUILD_VER=${BUILD_VER}$(date +%y%m%d%H%M%S)
}

SETUPENV_PATH=$(realpath ../venv_py3)
ENV_PYTHON=${SETUPENV_PATH}/bin/python
ENV_PIP=${SETUPENV_PATH}/bin/pip

BUILD_FD=build_src


echo -e "\n* Building Packages:"

if ! (test -x ${ENV_PYTHON} && test -x ${ENV_PIP}) ;then
    echo -e "\n-- Error!! failed to detect virtualenv, rebuild DEV setup\n"
    exit 1
fi

rm -rf ${BUILD_FD}
mkdir -m 775 -p ${BUILD_FD}/src

cp -rf src/${PKGNAME} ${BUILD_FD}/src/
cp -rf examples/ setup.* *.md LICENSE MANIFEST.in ${BUILD_FD}/

# set build version
sed -i "s|^__version__ = \".*|__version__ = \"${BUILD_VER}\"|g" \
    ${BUILD_FD}/src/${PKGNAME}/__init__.py

# create source package
${ENV_PYTHON} ${BUILD_FD}/setup.py sdist clean --all

# create wheel package
${ENV_PYTHON} ${BUILD_FD}/setup.py bdist_wheel clean --all

# create dist and clean
mv -f ${BUILD_FD}/dist .
rm -rf ${BUILD_FD}

echo -e "\n* Created packages: ${PKGNAME} ${BUILD_VER}\n"
