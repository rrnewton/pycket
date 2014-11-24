# This is a self contained nix build file that depends on, but is not
# part of, a 'nixpkgs' snapshot.

let 
   pkgs   = import <nixpkgs> {};
   stdenv = pkgs.stdenv;
in 
  stdenv.mkDerivation rec {
    name = "pycket";
    version = "0.1";
#    src = null;
#    src = "./src";

    srcPypy = pkgs.fetchhg 
           { url = https://bitbucket.org/pypy/pypy; 
             rev = "74619:092128f86b9d";
             sha256 = "1yjqhym8n2ycavzhcqvywwav3r2hsjadidkwyvz4pdhn5q138aap";
           };
    src = ./.;

    unpackPhase = ''
       mkdir $out
       cd $out
       echo "Unpack phase... in $out"
     '';

    buildInputs = [ pkgs.python  pkgs.which  pkgs.pypy  pkgs.pkgconfig  pkgs.libffi ];
    buildCommand = ''
      echo; 
      echo "================================================"
      echo "Beginning build of Pycket and Pypy dependencies.";
      echo "================================================"; echo
      echo "Current directory: "`pwd`", contents:"
      ls
      echo "Src directory: $src contents:"
      ls $src
      echo "Output path: $out"

#      echo $PATH | perl -ne "s/\:/\n/g; print"
      echo Python = `which python`
      mkdir -p $out/
      ls -l $out/

      echo "Copying downloaded working copy into output directory ($out/)..."
#      cp -r --no-preserve=mode,ownership ${src}/*-pycket/ $out/
      cp -r --no-preserve=mode,ownership ${src}/ $out/pycket/

      echo "Copying downloaded pypy source repo into output directory ($out/pypy)..."
      cp -r --no-preserve=mode,ownership ${srcPypy}/ $out/pypy/
      echo " ... Done copying."

      set -x
      chmod +x $out/pypy/rpython/bin/* $out/pypy/pypy/bin/*
      cd $out/pycket
      ln -s ../pypy pypy
      time make translate-jit

     '';
  }

# rec { }
