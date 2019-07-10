;;; .emacs --- Emacs initialization file.
;;; Author: mark a. foltz (spuddybuddy@ubertuber.org)
;;; Maintainer: mark a. foltz (spuddybuddy@ubertuber.org)
;;; https://github.com/spuddybuddy/dotfiles
;;; hacked on continuously from 1992 - today


;; Added by Package.el.  This must come before configurations of
;; installed packages.  Don't delete this line.  If you don't want it,
;; just comment it out by adding a semicolon to the start of the line.
;; You may delete these explanatory comments.
(package-initialize)

(defvar mf-home-dir (getenv "HOME"))
(defvar mf-emacs-path
  (concat mf-home-dir
	  (if (eq system-type 'windows-nt)
	      "\\github\\spuddybuddy\\dotfiles\\emacs"
	      "/github/spuddybuddy/dotfiles/emacs")))
(add-to-list 'load-path mf-emacs-path)
(require 'mf-emacs "emacs.el")
(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(auto-revert-verbose nil)
 '(blink-cursor-mode nil)
 '(c-basic-offset 2)
 '(c-offsets-alist
   (quote
    ((access-label . -1)
     (arglist-intro . 4)
     (innamespace . 0))))
 '(column-number-mode t)
 '(comment-fill-column 80)
 '(compilation-skip-threshold 2)
 '(custom-browse-order-groups (quote first))
 '(default-frame-alist
    (quote
     ((tool-bar-lines . 0)
      (menu-bar-lines . 0)
      (width . 102)
      (height . 69)
      (cursor-color . "gold1")
      (pointer-color . "gold1"))))
 '(dirtrack-list (quote ("\\[[A-Za-z@-]+ \\([^]]+\\)\\]\\$" 1)))
 '(display-time-24hr-format t)
 '(display-time-mail-file (quote none))
 '(display-time-mode t)
 '(fill-column 80)
 '(font-lock-global-modes (quote (not speedbar-mode gyp-mode)))
 '(font-lock-maximum-size nil)
 '(global-auto-revert-mode t)
 '(global-font-lock-mode t nil (font-lock))
 '(ido-default-buffer-method (quote selected-window))
 '(ido-default-file-method (quote selected-window))
 '(ido-enable-regexp t)
 '(ido-enabled (quote both) nil (ido))
 '(ido-mode (quote both) nil (ido))
 '(indent-tabs-mode nil)
 '(inhibit-startup-screen t)
 '(javascript-indent-level 2)
 '(js-expr-indent-offset 4)
 '(js-indent-level 2)
 '(line-number-mode t)
 '(matlab-indent-function t)
 '(matlab-shell-command-switches (quote ("-nojvm" "-glnx86")))
 '(menu-bar-mode nil)
 '(mouse-wheel-mode t nil (mwheel))
 '(ns-alternate-modifier (quote super))
 '(ns-command-modifier (quote meta))
 '(package-selected-packages (quote (markdown-mode js2-mode)))
 '(py-indent-offset 2 t)
 '(python-indent-offset 2)
 '(scroll-bar-mode (quote right))
 '(sh-basic-offset 2)
 '(show-paren-mode t)
 '(tool-bar-mode nil)
 '(toolbar-captioned-p t)
 '(toolbar-visible-p nil)
 '(use-file-dialog nil)
 '(user-full-name "mark a. foltz")
 '(warning-suppress-types nil)
 '(which-func-modes t)
 '(which-function-mode t)
 '(whitespace-modes
   (quote
    (ada-mode asm-mode autoconf-mode awk-mode c-mode c++-mode cc-mode change-log-mode cperl-mode electric-nroff-mode emacs-lisp-mode f90-mode fortran-mode html-mode html3-mode java-mode jde-mode ksh-mode latex-mode LaTeX-mode lisp-mode m4-mode makefile-mode modula-2-mode nroff-mode objc-mode pascal-mode perl-mode prolog-mode python-mode scheme-mode sgml-mode sh-mode shell-script-mode simula-mode tcl-mode tex-mode texinfo-mode vrml-mode xml-mode javascript-mode css-mode nxml-mode)))
 '(whitespace-style
   (quote
    (face trailing tabs lines-tail newline empty space-after-tab space-before-tab))))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(default ((t (:inherit nil :stipple nil :background "#202020" :foreground "wheat2" :inverse-video nil :box nil :strike-through nil :overline nil :underline nil :slant normal :weight normal :height 170 :width normal :foundry "nil" :family "Andale Mono"))))
 '(comint-highlight-prompt ((t (:foreground "gold1" :weight bold))))
 '(custom-comment ((t (:background "black"))))
 '(custom-group-tag ((((min-colors 88) (class color) (background light)) (:inherit variable-pitch :foreground "SkyBlue" :weight bold :height 1.2))))
 '(custom-state ((((class color) (background light)) (:foreground "PaleGreen3"))))
 '(custom-variable-tag ((((min-colors 88) (class color) (background light)) (:foreground "CornflowerBlue" :weight bold))))
 '(font-lock-builtin-face ((t (:foreground "PaleGreen"))))
 '(font-lock-comment-face ((t (:foreground "Gray"))))
 '(font-lock-constant-face ((t (:foreground "Green"))))
 '(font-lock-doc-face ((t (:foreground "gray80"))))
 '(font-lock-function-name-face ((t (:foreground "cyan1"))))
 '(font-lock-keyword-face ((t (:foreground "LightSkyBlue"))))
 '(font-lock-string-face ((t (:foreground "GoldenRod"))))
 '(font-lock-type-face ((t (:foreground "DarkOrange"))))
 '(font-lock-variable-name-face ((t (:foreground "Plum"))))
 '(font-lock-warning-face ((t (:foreground "Aquamarine"))))
 '(highlight ((((class color) (min-colors 88) (background light)) (:background "#007800"))))
 '(lazy-highlight ((((class color) (min-colors 88) (background light)) (:background "#003000"))))
 '(link ((((class color) (min-colors 88) (background light)) (:foreground "CornflowerBlue" :underline t))))
 '(match ((((class color) (min-colors 88) (background light)) (:background "#303030"))))
 '(minibuffer-prompt ((((background dark)) (:foreground "cyan" :weight bold))))
 '(mode-line ((t (:background "#003000" :foreground "SpringGreen"))))
 '(nxml-attribute-local-name-face ((t (:inherit font-lock-variable-name-face))))
 '(nxml-attribute-value-delimiter-face ((t (:inherit font-lock-string-face))))
 '(nxml-comment-content-face ((t (:inherit font-lock-comment-face))))
 '(nxml-comment-delimiter-face ((t (:inherit font-lock-comment-face))))
 '(nxml-delimited-data-face ((t (:inherit font-lock-string-face))))
 '(nxml-element-colon-face ((t (:inherit nxml-name-face :weight bold))))
 '(nxml-element-local-name-face ((t (:inherit nxml-name-face :weight bold))))
 '(nxml-element-prefix-face ((t (:inherit nxml-name-face :weight bold))))
 '(nxml-name-face ((t (:inherit font-lock-keyword-face))))
 '(nxml-namespace-attribute-colon-face ((t (:inherit font-lock-variable-name-face))))
 '(nxml-namespace-attribute-prefix-face ((t (:inherit font-lock-variable-name-face))))
 '(nxml-namespace-attribute-xmlns-face ((t (:inherit font-lock-variable-name-face))))
 '(nxml-tag-delimiter-face ((t (:inherit font-lock-keyword-face))))
 '(region ((t (:background "DarkGreen"))))
 '(secondary-selection ((t (:background "DimGray"))))
 '(whitespace-highlight ((((class color) (background dark)) (:background "DarkSlateGray2"))))
 '(widget-field ((((class grayscale color) (background light)) (:background "gray15"))))
 '(widget-single-line-field ((((class grayscale color) (background light)) (:background "gray15")))))
(put 'upcase-region 'disabled nil)
(put 'erase-buffer 'disabled nil)

(when (eq system-type 'windows-nt)
  (progn
    (set-face-attribute 'default nil :foundry "Outline" :family "Consolas")
    (set-frame-font "Consolas-11.5" nil t)))

;; Hack to detect Crostini (Linux-on-ChromeOS).  Need to do better to detect
;; screen dpi.
(when (equal (system-name) "penguin")
  (let ((default-font-spec (font-spec 
                             :family "Bitstream Vera Sans Mono"
                             :foundry "Bitstream"
                             :width 'normal
                             :size 19))
        (default-fontset "-bitstream-Bitstream Vera Sans Mono-normal-normal-normal-*-19-*-*-*-*-*-*"))
    (progn
      (set-face-font 'default default-font-spec nil)
      (set-frame-font default-font-spec t nil)
      (setq default-frame-alist
            `((tool-bar-lines . 0)
              (menu-bar-lines . 0)
              (width . 102)
              (height . 48)
              (cursor-color . "gold1")
              (pointer-color . "gold1")
              (vertical-scroll-bars . right)
              (font . ,default-fontset)))
      (setq initial-frame-alist
            `((tool-bar-lines . 0)
              (menu-bar-lines . 0)
              (width . 102)
              (height . 48)
              (cursor-color . "gold1")
              (pointer-color . "gold1")
              (vertical-scroll-bars . right)
              (font . ,default-fontset))))))

;; Always start the server.
(server-start)
