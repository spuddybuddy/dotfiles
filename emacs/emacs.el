;;; emacs.el
;;; mark a. foltz (spuddybuddy@ubertuber.org)
;;; http://ubertuber.org/
;;; hacked on continuously from 1992 - 2006
;; list of dependent emacs lisp files and packages for my setup.
;; TODO: keep up to date!
;; buffer-search.el
;; clean-buffers.el
;; compile-highlight.el
;; filladapt.el
;; matlab.el
;; resync.el
;; scroll-in-place.el
;; ssh.el
;; nxml-mode-20041004
;; nxhtml-0.78
;;;;;;;;;;;;;;;;;;;;;; generic mode
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
(autoload 'resync-files "resync" nil t)
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
(mf-delete-auto-mode 'javascript-generic-mode)
(autoload 'javascript-mode "javascript" nil t)
(add-to-list 'auto-mode-alist '("\\.js\\'" . javascript-mode))
;; css mode
(add-to-list 'auto-mode-alist '("\\.css\\'" . css-mode))
(autoload 'css-mode "css-mode" nil t)
;; nxhtml mode for html
;; TODO: Find a copy of nxhtml-2.08-100425.zip or a another HTML editing mode
;; (load (concat mf-emacs-path "/3p/nxhtml-0.78/nxhtml-autoload"))
;;;;;;;;;;;;;;;;;;;;;; mode hooks
;; python mode hook
;; (add-hook 'python-mode-hook
;; 	  (lambda ()
;; 	    (auto-fill-mode)
;; 	    ;; keep things wrapped at 80 columns
;; 	    (setq fill-column 80)
;; 	    ;; Don't stop at underscores for forward-word and backward-word!
;; 	    (modify-syntax-entry ?\_ "_" py-mode-syntax-table)))
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
