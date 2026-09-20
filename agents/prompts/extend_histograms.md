Please review the documentation in tools/metrics/histograms/README.md, paying
particular attention to the section titled "Histogram Expiry" and "How to extend
expired histograms."

Please look at tools/metrics/histograms/metadata/media/histograms.xml.  I want
to extend the expiration of the histograms in the list below.

If the histogram has an expires_after attribute ON or AFTER 2026-01-02, then
extend the histogram to expire 364 days from now by setting the expires_after
attribute to 2027-02-01.

If the histogram has an expires_after attribute that is BEFORE 2026-01-02, then
perform the following steps:

1. Add to the histogram description the following message: "Warning: this
   histogram was expired from <current expires_after date> to 2026-02-02; data
   may be missing."  Replace <current expires_after date> with the current value
   of the expires_after attribute.
2. Set the expires_after attribute to 2027-02-01.

- Cast.Channel.LaunchSession.Flags
- MediaRouter.Cast.Discovery.SinkSource
- MediaRouter.CastStreaming.Session.Length.Screen
- MediaRouter.CastStreaming.Session.Length.Tab
- MediaRouter.PresentationRequest.UrlBySink2
- Media.Audio.Capture.SCK.ContentEnumerationTimedOut
- Media.Audio.Capture.SCK.ContentEnumerationTimeMs
- MediaRouter.Sink.SelectedType
- MediaRouter.Sink.SelectedType.CastHarmony
- MediaRouter.Sink.SelectedType.GlobalMediaControls
- MediaRouter.Dial.FetchAppInfo
- MediaRouter.CastStreaming.Session.Length.Tab
- MediaRouter.CastStreaming.Session.Length.Screen
- Cast.Sender.VideoEncodeAcceleratorInitializeSuccess
- Media.Remoting.AudioBitrate
- Media.Remoting.ShortSessionDuration
- Media.Remoting.SessionStopTrigger.Duration10To15Sec
- Media.Remoting.SessionStopTrigger
- Media.Remoting.VideoCodec
- Media.Remoting.VideoCodecProfile
- Media.Remoting.SessionStopTrigger.Duration3To5Sec
- Media.Remoting.TrackConfiguration
- Media.Remoting.VideoBitrate
- Media.Remoting.TimeUntilFirstPlayout
- Media.Remoting.AudioChannelLayout
- Media.Remoting.TimeUntilRemoteInitialized
- Media.Remoting.VideoAspectRatio
- Media.Remoting.RemotePlaybackEnabledByPage
- Media.Remoting.SessionStopTrigger.Duration5To10Sec
- Media.Remoting.AudioSamplesPerSecond
- Media.Remoting.SessionStopTrigger.Duration1To3Sec
- Media.Remoting.SessionDuration
- Media.Remoting.SessionStartTrigger
- Media.Remoting.SessionStopTrigger.Duration100MilliSecTo1Sec
- Media.Remoting.AudioCodec
- Media.Remoting.AudioSamplesPerSecondUnexpected
- Media.Remoting.SessionStopTrigger.Duration0To100MilliSec
- MediaRouter.MirroringService.DisabledHardwareCodecAndRenegotiated
- MediaRouter.MirroringService.GpuFactoryContextLost
- Media.Remoting.SessionStartFailedReason
- CastStreaming.Sender.Audio.AverageEndToEndLatency
- CastStreaming.Sender.Audio.AverageEncodeTime
- CastStreaming.Sender.Video.RetransmittedPacketsPercentage
- CastStreaming.Sender.Audio.TransmissionRate
- CastStreaming.Sender.Audio.LateFramesPercentage
- CastStreaming.Sender.Audio.RetransmittedPacketsPercentage
- CastStreaming.Sender.Video.AverageEncodeTime
- CastStreaming.Sender.Video.LateFramesPercentage
- CastStreaming.Sender.Video.ExceededPlayoutDelayPacketsPercentage
- CastStreaming.Sender.Video.AverageNetworkLatency
- CastStreaming.Sender.Audio.AverageNetworkLatency
- CastStreaming.Sender.Video.AverageEndToEndLatency
- CastStreaming.Sender.Video.TransmissionRate
- CastStreaming.Sender.Audio.ExceededPlayoutDelayPacketsPercentage
