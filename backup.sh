# get the name of the current folder
sourcedir=$(dirname $(realpath "$0"));

# grab the name of the target directory passed in by the user
targetdir="${1}/${sourcedir##*/}";

# go into the source directory
cd $sourcedir;

# run rsync and delete any files that have been deleted locally
sshpass -e rsync -aP --delete $sourcedir $targetdir;