!/bin/bash
# Usage: forward-include.sh <new-include-file> <old-path>

new_file=$1
old_path=$2
filename=$old_path/$(basename $1)
guard=$(echo "$filename" | sed 'y/abcdefghijklmnopqrstuvwxyz\.\//ABCDEFGHIJKLMNOPQRSTUVWZYZ__/')
guard="$guard"_
cat <<EOF > $filename
// Copyright 2024 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef $guard
#define $guard

#include "$new_file"

#endif  // $guard
EOF
