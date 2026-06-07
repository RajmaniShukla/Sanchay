; ===========================================================================
; Sanchay — NSIS Installer Script
; Version: 1.0.0
; Produces: SanchaySetup-1.0.0.exe
;
; Requirements: NSIS 3.x  (https://nsis.sourceforge.io/Download)
;
; Build:
;   cd D:\Projects\Sanchay\installer
;   "C:\Program Files (x86)\NSIS\makensis.exe" sanchay_installer.nsi
;   -- or --
;   "C:\Program Files\NSIS\makensis.exe" sanchay_installer.nsi
;
; Output: installer\SanchaySetup-1.0.0.exe
; ===========================================================================

; ---- Modern UI ----------------------------------------------------------------
!include "MUI2.nsh"
!include "FileFunc.nsh"

; ---- Metadata ----------------------------------------------------------------
!define APP_NAME        "Sanchay"
!define APP_VERSION     "1.0.0"
!define APP_PUBLISHER   "Sanchay Systems"
!define APP_URL         "https://github.com/sanchay"
!define APP_EXE         "Sanchay.exe"
!define APP_ICON        "..\dist\Sanchay\_internal\app\resources\icons\sanchay.ico"
!define INSTALL_DIR     "$PROGRAMFILES64\${APP_NAME}"
!define UNINSTALL_KEY   "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
!define REG_KEY         "Software\${APP_NAME}"
!define OUTPUT_FILE     "SanchaySetup-${APP_VERSION}.exe"

; ---- Compiler settings --------------------------------------------------------
Name              "${APP_NAME} ${APP_VERSION}"
OutFile           "${OUTPUT_FILE}"
InstallDir        "${INSTALL_DIR}"
InstallDirRegKey  HKLM "${REG_KEY}" "InstallDir"
RequestExecutionLevel admin
Unicode           True
SetCompressor     /SOLID lzma
SetCompressorDictSize 128

; ---- MUI Settings -------------------------------------------------------------
!define MUI_ICON                   "${APP_ICON}"
!define MUI_UNICON                 "${APP_ICON}"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE      "Welcome to ${APP_NAME} ${APP_VERSION} Setup"
!define MUI_WELCOMEPAGE_TEXT       "This will install ${APP_NAME} — Inventory & Asset Management System on your computer.$\r$\n$\r$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN         "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT    "Launch ${APP_NAME} now"
!define MUI_FINISHPAGE_SHOWREADME  ""

; ---- Installer pages ----------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE      "..\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; ---- Uninstaller pages --------------------------------------------------------
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; ---- Languages ----------------------------------------------------------------
!insertmacro MUI_LANGUAGE "English"

; ===========================================================================
; INSTALLER SECTION
; ===========================================================================
Section "Sanchay (required)" SecMain
    SectionIn RO  ; required — cannot be deselected

    SetOutPath "$INSTDIR"

    ; ---- Copy all dist files --------------------------------------------------
    File /r "..\dist\Sanchay\*.*"

    ; ---- Write registry entries -----------------------------------------------
    WriteRegStr HKLM "${REG_KEY}" "InstallDir"  "$INSTDIR"
    WriteRegStr HKLM "${REG_KEY}" "Version"     "${APP_VERSION}"

    ; ---- Add/Remove Programs entry --------------------------------------------
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayName"          "${APP_NAME}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayVersion"        "${APP_VERSION}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "Publisher"             "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "URLInfoAbout"          "${APP_URL}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "InstallLocation"       "$INSTDIR"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "DisplayIcon"           "$INSTDIR\${APP_EXE}"
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "UninstallString"       '"$INSTDIR\Uninstall.exe"'
    WriteRegStr   HKLM "${UNINSTALL_KEY}" "QuietUninstallString"  '"$INSTDIR\Uninstall.exe" /S'
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify"              1
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair"              1

    ; ---- Estimated install size (KB) ------------------------------------------
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "EstimatedSize" "$0"

    ; ---- Write uninstaller ----------------------------------------------------
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; ---- Start Menu shortcuts -------------------------------------------------
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
                    "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" \
                    "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0

    ; ---- Desktop shortcut -----------------------------------------------------
    CreateShortcut  "$DESKTOP\${APP_NAME}.lnk" \
                    "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

SectionEnd

; ===========================================================================
; UNINSTALLER SECTION
; ===========================================================================
Section "Uninstall"

    ; ---- Ask about user data --------------------------------------------------
    MessageBox MB_YESNO|MB_ICONQUESTION \
        "Do you want to keep your data (database, backups, exports, logs)?$\r$\n$\r$\nClick Yes to keep them.$\r$\nClick No to delete everything." \
        IDYES keep_data

    ; Delete user data if they chose No
    RMDir /r "$INSTDIR\data"
    RMDir /r "$INSTDIR\logs"
    RMDir /r "$INSTDIR\backups"
    RMDir /r "$INSTDIR\exports"
    RMDir /r "$INSTDIR\app"

    keep_data:

    ; ---- Remove program files -------------------------------------------------
    RMDir /r "$INSTDIR\_internal"
    Delete   "$INSTDIR\${APP_EXE}"
    Delete   "$INSTDIR\Uninstall.exe"
    RMDir    "$INSTDIR"   ; removes dir only if empty

    ; ---- Remove shortcuts -----------------------------------------------------
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
    RMDir  "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    ; ---- Remove registry entries ----------------------------------------------
    DeleteRegKey HKLM "${UNINSTALL_KEY}"
    DeleteRegKey HKLM "${REG_KEY}"

SectionEnd
