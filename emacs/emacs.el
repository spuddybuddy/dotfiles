;;; emacs.el
;;; mark a. foltz (spuddybuddy@ubertuber.org)
;;; http://ubertuber.org/
;;; hacked on continuously from 1992 - today
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

;; javascript mode
;; TODO: Install/enable js2-mode
;; (mf-delete-auto-mode 'javascript-generic-mode)
;; (autoload 'javascript-mode "javascript" nil t)
;; (add-to-list 'auto-mode-alist '("\\.js\\'" . javascript-mode))

;; shell-mode hook.
;; Enable directory tracking that actually works by parsing the shell prompt.
(require 'dirtrack)
(add-hook 'shell-mode-hook
          (lambda ()
            (setq shell-dirtrack-mode nil)
            (dirtrack-mode)))

;;;;;;;;;;;;;;;;;;;;;; google specific stuff (at the end)
(if (file-readable-p "/home/mfoltz")
    (progn
      (add-to-list 'load-path (concat mf-emacs-path "/google"))
      (require 'mf-google)))

(provide 'mf-emacs)
