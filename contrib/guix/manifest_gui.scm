(use-modules (gnu packages bison)
             ((gnu packages gnome) #:select (librsvg-2.40))
             ((gnu packages image) #:select (libicns))
             ((gnu packages imagemagick) #:select (imagemagick))
             ((gnu packages compression) #:select (xz zip))
             (gnu packages gawk)
             ((gnu packages installers) #:select (nsis-x86_64))
             (gnu packages ninja)
             (gnu packages pkg-config)
             ((gnu packages python) #:select (python-minimal))
             ((gnu packages python-xyz) #:select (python-lief))
             (guix build-system font)
             (guix download)
             ((guix licenses) #:prefix license:)
             (guix packages))

(define-public font-tuffy
  (package
    (name "font-tuffy")
    (version "20120614")
    (source
     (origin
       (method url-fetch)
       (uri (string-append "http://tulrich.com/fonts/tuffy-" version ".tar.gz"))
       (file-name (string-append name "-" version ".tar.gz"))
       (sha256
        (base32
         "02vf72bgrp30vrbfhxjw82s115z27dwfgnmmzfb0n9wfhxxfpyf6"))))
    (build-system font-build-system)
    (home-page "http://tulrich.com/fonts/")
    (synopsis "The Tuffy Truetype Font Family")
    (description
     "Thatcher Ulrich's first outline font design. He started with the goal of producing a neutral, readable sans-serif text font. There are lots of \"expressive\" fonts out there, but he wanted to start with something very plain and clean, something he might want to actually use. ")
    (license license:public-domain)))

(packages->manifest
 (append
  (list ;; Compression and archiving
        xz
        ;; Build tools
        ninja
        ;; Rendering icons from SVG
        imagemagick
        libicns
        librsvg-2.40
        ;; Packaging scripts
        python-minimal ;; (3.11)
        ;; Tests
        python-lief)
  (let ((target (getenv "HOST")))
    (cond ((string-suffix? "-mingw32" target)
           (list font-tuffy zip
                 nsis-x86_64))
          ((string-contains target "-linux-")
           (list bison
                 gawk
                 pkg-config))
          ((string-contains target "darwin")
           (list zip))
          (else '())))))
