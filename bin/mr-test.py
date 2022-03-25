#!/usr/bin/python3

DEFINE_bool debug false
DEFINE_string build "Default"
DEFINE_string test ""
DEFINE_enum type --enum="unit,component,content,integration,polymer,blink,layout" unit
GBASH_PASSTHROUGH_UNKNOWN_FLAGS=1
gbash::init_google "$@"

# TODO: Where are tests on Mac OS X / Windoze?
gdb="/usr/bin/gdb"
build_path="unknown"
[ -d $HOME/chrome/src/out/$FLAGS_build ] && build_path="$HOME/chrome/src/out/$FLAGS_build"

if [ "$build_path" == "unknown" ]; then
    gbash::quiet_die "Unable to find where the unit tests are."
fi

prefix=""
if (( $FLAGS_debug )); then
  prefix="${gdb} --args "
fi

function make_binary_path() {
  local test_path=${build_path}/$1;
  if [ ! -x "${test_path}" ]; then
      gbash::quiet_die "Looks like you don't have $test_path built!"
  fi
  echo ${prefix}${test_path}
}

VMODULE_PATTERNS = [
    "cast_*",
    "cast_cert*",
    "dial*",
    "media_r*",
    "offscreen_tab*",
    "?resentation*",
    "local_presentation*"
    "media_r*",
]

COMMON_FLAGS = [
    "--enable-logging",
    "--also-log-to-stderr",
]

BROWSER_TEST_SPECS = [
  'browser_tests': [
      'TabCaptureApiTest*',
      'CastDialog*',
      'MediaRouter*',
      'PresentationReceiver*',
      'GlobalMediaControlsDialogTest*',
      'SystemTrayTrayCastMediaRouterChromeOSTest*',
      ],
  'interactive_ui_tests': [
      'MediaRouterIntegration*',
      'MediaRouterE2E*',
   ]





]

UNIT_TEST_SPECS = [
  'unit_tests': [
      'AccessCode*',
      'AppActivityTest*',
      'CastActivity*',
      'CastAnalytics*',
      'CastApp*',
      'CastDialog*',
      'CastInternal*',
      'CastMedia*',
      'CastSession*',
      'CastToolbar*',
      'ChromeLocalPresentationManager*',
      'ChromeMediaRouter*',
      'DeviceDescription*',
      'Dial*',
      'DiscoveryNetwork*',
      'DnsSdRegistry*',
      'DualMediaSinkService*',
      'MediaCastModeTest*',
      'MediaRouter*',
      'MediaSink*',
      'MirroringActivityTest*',
      'NetworkServiceQuic*',
      'OpenScreen*',
      'PresentationService*',
      'QueryResultManagerTest*',
      'SafeDial*',
      'WebContentsDisplayObserverViewTest*',
      'WiredDisplay*',
      ],




]


def RunUnitTests():


def RunLayoutTests():


def




# TODO: Add support for polymer, browser, layout tests
binary=""
test_spec="$FLAGS_test"
if [ $FLAGS_type == "unit" ]; then
    binary=$(make_binary_path unit_tests)
    [ -z "$test_spec" ] && test_spec="MediaR*:*Presentation*:MediaSource*:MediaSink*:MediaCast*:DeviceDescription*:IssueManager*:Dial*:SafeDial*:QueryResultManager*:Cast*:OpenScreen*:NetworkServiceQuicPacketWriterTest*:ChromeTlsClientConnectionTest*:ChromeTlsConnectionFactoryTest*";
    set -x
    exec ${binary} \
         ${common_flags} \
         --gtest_filter=${test_spec} \
         "${GBASH_ARGV[@]}"
elif [ $FLAGS_type == "component" ]; then
    binary=$(make_binary_path components_unittests)
    [ -z "$test_spec" ] && test_spec="CastChannel*";
    set -x
    exec ${binary} \
         ${common_flags} \
         --gtest_filter=${test_spec} \
         "${GBASH_ARGV[@]}"
elif [ $FLAGS_type == "content" ]; then
    binary=$(make_binary_path content_unittests)
    [ -z "$test_spec" ] && test_spec="Presentation*";
    set -x
    exec ${binary} \
         ${common_flags} \
         --gtest_filter=${test_spec} \
         "${GBASH_ARGV[@]}"
elif [ $FLAGS_type == "blink" ]; then
    binary$(make_binary_path webkit_unit_tests)
    [ -z "$test_spec" ] && test_spec="Presentation*";
    set -x
    exec ${binary} \
         ${common_flags} \
         --gtest_filter=${test_spec} \
         "${GBASH_ARGV[@]}"
elif [ $FLAGS_type == "polymer" ]; then
    binary=$(make_binary_path browser_tests)
    [ -z "$test_spec" ] && test_spec="MediaRouterElements*";
    set -x
    exec ${binary} \
         ${common_flags} \
         --gtest_filter=${test_spec} \
         "${GBASH_ARGV[@]}"
elif [ $FLAGS_type == "integration" ]; then
    binary=$(make_binary_path browser_tests)
    [ -z "$test_spec" ] && test_spec="MediaRouterIntegration*";
    set -x
    exec ${binary} \
         ${common_flags} \
         --gtest_filter=${test_spec} \
         --run-manual \
         "${GBASH_ARGV[@]}"
elif [ $FLAGS_type == "layout" ]; then
  binary="third_party/blink/tools/run_web_tests.py"
    [ -z "$test_spec" ] && test_spec="presentation/ virtual/presentation/";
    set -x
    exec ${binary} \
      -t ${FLAGS_build} \
      --verbose \
      --details \
      --driver-logging \
      --additional-driver-flag=--enable-logging \
      --additional-driver-flag=--also-log-to-stderr \
      --additional-driver-flag=--vmodule=presentation*=2,Presentation*=2,render_frame*=2 \
      ${test_spec} \
      "${GBASH_ARGV[@]}"
else
  gbash::quiet_die "Don't know how to run $FLAGS_type yet :-("
fi
