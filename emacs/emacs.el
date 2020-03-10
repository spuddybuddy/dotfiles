;;; emacs.el - Emacs initialization (outside of custom).
;;; Author: mark a. foltz (spuddybuddy@ubertuber.org)
;;; Maintainer: mark a. foltz (spuddybuddy@ubertuber.org)
;;; http://ubertuber.org/
;;; https://github.com/spuddybuddy

;; list of dependent emacs lisp files and packages.
;; clean-buffers.el
;; ssh.el - https://github.com/ieure/ssh-el
;; js2-mode - https://github.com/mooz/js2-mode

;;;;;;;;;;;;;;;;;;;;;; generic mode
;; TODO: What is this?  Is it still required?
(require 'generic-x)

;;;;;;;;;;;;;;;;;;;;;; global key remappings
(define-key global-map "\C-t" 'copy-region-as-kill)
(define-key global-map "\C-xo" 'transpose-chars)
(define-key global-map "\C-v" 'other-window)
(define-key global-map [(control shift v)] 'other-frame)
(define-key global-map "\M-v" 'goto-line)
(define-key global-map [M-right] 'end-of-line)
(define-key global-map [M-left] 'beginning-of-line)

;;;;;;;;;;;;;;;;;;;;;; non-mode-related setups
(autoload 'clean-buffers "clean-buffers" nil t)
(autoload 'ssh "ssh" nil t)
(put 'eval-expression 'disabled nil)
(put 'downcase-region 'disabled nil)
(put 'narrow-to-region 'disabled nil)
;; Interactive Do - smarter find-file and switch-buffers
;; http://www.cua.dk/ido.html
(require 'ido)
;; Restore sessions across restart.
(require 'desktop)

;;;;;;;;;;;;;;;;;;;;;;; mode-specific setups
;; Removes the given mode from auto-mode-alist.
(defun mf-delete-auto-mode (mode)
  (rassq-delete-all mode auto-mode-alist))

;; text mode
(define-key text-mode-map [M-up] 'forward-sentence)
(define-key text-mode-map [M-down] 'backward-sentence)

;; js2 mode
;;(mf-delete-auto-mode 'javascript-mode)
(add-to-list 'auto-mode-alist '("\\.js\\'" . js2-mode))

;; Bikeshed
(add-to-list 'auto-mode-alist '("\\.bs\\'" . markdown-mode))

;; shell-mode hook.
;; Enable directory tracking that actually works by parsing the shell prompt.
(require 'dirtrack)
(add-hook 'shell-mode-hook
          (lambda ()
            (setq shell-dirtrack-mode nil)
            (dirtrack-mode)))

;; MELPA packages.
;; Documentation: https://stable.melpa.org/
(require 'package)
(add-to-list 'package-archives
             '("melpa-stable" . "https://stable.melpa.org/packages/") t)
(package-initialize)

;; GN-mode
(defvar mf-gn-emacs-path (concat mf-home-dir "/gn/misc/emacs"))

(if (file-readable-p mf-gn-emacs-path)
    (progn
      (add-to-list 'load-path mf-gn-emacs-path)
      (require 'gn-mode)))

;;;;;;;;;;;;;;;;;;;;;; google specific stuff (at the end)
;; TODO: Figure out how to use Google site-lisp on Mac
(defvar mf-google-emacs-path (concat mf-home-dir "/gob/dotfiles/emacs/google"))
(if (and
     (file-readable-p mf-google-emacs-path)
     (not (eq system-type 'darwin))
     (not (eq system-type 'windows-nt)))
    (progn
      (add-to-list 'load-path mf-google-emacs-path)
      (require 'mf-google)))

(provide 'mf-emacs)
