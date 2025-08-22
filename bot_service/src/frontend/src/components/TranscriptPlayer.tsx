import React, { useState, useRef, useEffect } from "react";
import { Transcript } from "../types";
import {
  X,
  Play,
  Pause,
  Download,
  Volume2,
  VolumeX,
  Maximize2,
  FileText,
  Info,
  BarChart3,
  Edit,
  Check,
  Search,
} from "lucide-react";

interface TranscriptPlayerProps {
  transcript: Transcript;
  onClose: () => void;
  onAccept?: (transcriptId: string) => void;
}

interface SubtitleItem {
  id: number;
  startTime: number;
  endTime: number;
  text: string;
}

const TranscriptPlayer: React.FC<TranscriptPlayerProps> = ({
  transcript,
  onClose,
  onAccept,
}) => {
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const [activeSubtitle, setActiveSubtitle] = useState<SubtitleItem | null>(
    null
  );
  const [fullscreen, setFullscreen] = useState(false);
  const [activeTab, setActiveTab] = useState<
    "player" | "file" | "transcription"
  >("player");
  const [searchQuery, setSearchQuery] = useState("");
  const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Mock SRT subtitles
  const subtitles: SubtitleItem[] = [
    {
      id: 1,
      startTime: 0,
      endTime: 5,
      text: "Welcome to our transcript service.",
    },
    {
      id: 2,
      startTime: 5,
      endTime: 10,
      text: "This is a sample subtitle for your media file.",
    },
    {
      id: 3,
      startTime: 10,
      endTime: 15,
      text: "You can see the synchronized text here.",
    },
    {
      id: 4,
      startTime: 15,
      endTime: 20,
      text: "This demonstrates the SRT subtitle feature.",
    },
    {
      id: 5,
      startTime: 20,
      endTime: 25,
      text: "Thank you for using TranscribeAI.",
    },
  ];

  useEffect(() => {
    const media = mediaRef.current;
    if (!media) return;

    const updateTime = () => setCurrentTime(media.currentTime);
    const updateDuration = () => setDuration(media.duration);
    const handleEnded = () => setPlaying(false);

    media.addEventListener("timeupdate", updateTime);
    media.addEventListener("loadedmetadata", updateDuration);
    media.addEventListener("ended", handleEnded);

    return () => {
      media.removeEventListener("timeupdate", updateTime);
      media.removeEventListener("loadedmetadata", updateDuration);
      media.removeEventListener("ended", handleEnded);
    };
  }, []);

  useEffect(() => {
    const currentSubtitle = subtitles.find(
      (sub) => currentTime >= sub.startTime && currentTime <= sub.endTime
    );
    setActiveSubtitle(currentSubtitle || null);
  }, [currentTime]);

  const togglePlayback = () => {
    if (!mediaRef.current) return;

    if (playing) {
      mediaRef.current.pause();
    } else {
      mediaRef.current.play();
    }
    setPlaying(!playing);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (mediaRef.current) {
      mediaRef.current.currentTime = time;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const vol = parseFloat(e.target.value);
    setVolume(vol);
    if (mediaRef.current) {
      mediaRef.current.volume = vol;
    }
  };

  const toggleMute = () => {
    if (mediaRef.current) {
      mediaRef.current.muted = !muted;
      setMuted(!muted);
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement && containerRef.current) {
      containerRef.current.requestFullscreen();
      setFullscreen(true);
    } else {
      document.exitFullscreen();
      setFullscreen(false);
    }
  };

  const jumpToSubtitle = (subtitle: SubtitleItem) => {
    if (mediaRef.current) {
      mediaRef.current.currentTime = subtitle.startTime;
      setCurrentTime(subtitle.startTime);
    }
  };

  const downloadSrt = () => {
    const srtContent = subtitles
      .map((sub, index) => {
        const startTime = formatSrtTime(sub.startTime);
        const endTime = formatSrtTime(sub.endTime);
        return `${index + 1}\n${startTime} --> ${endTime}\n${sub.text}\n`;
      })
      .join("\n");

    const blob = new Blob([srtContent], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${transcript.fileName.split(".")[0]}.srt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatSrtTime = (seconds: number) => {
    const date = new Date(seconds * 1000);
    const hours = date.getUTCHours().toString().padStart(2, "0");
    const minutes = date.getUTCMinutes().toString().padStart(2, "0");
    const secs = date.getUTCSeconds().toString().padStart(2, "0");
    return `${hours}:${minutes}:${secs}`;
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const isVideo = transcript.fileType === "video";

  // Filter subtitles based on search query
  const filteredSubtitles = subtitles.filter((subtitle) =>
    subtitle.text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div
      ref={containerRef}
      className={`fixed inset-0 bg-black z-50 ${
        fullscreen ? "" : "bg-opacity-75"
      } flex items-center justify-center p-6`}
    >
      <div
        className={`p-6 bg-white rounded-2xl shadow-xl w-full ${
          fullscreen ? "h-full" : "max-w-6xl max-h-[85vh]"
        } flex flex-col`}
      >
        {!fullscreen && (
          <div className="flex items-center justify-between p-6 border-b border-gray-200 flex-shrink-0">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                {transcript.fileName}
              </h2>
              <p className="text-gray-600">
                Playing with synchronized subtitles
              </p>
            </div>
            <div className="flex items-center space-x-3">
              {!transcript.accepted && (
                <button
                  onClick={() => onAccept?.(transcript.id)}
                  className="group flex items-center px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all duration-200 shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
                >
                  <Check className="w-4 h-4 mr-2 group-hover:scale-110 transition-transform duration-200" />
                  <span className="font-medium text-sm">Accept</span>
                </button>
              )}
              <button
                onClick={downloadSrt}
                className="group flex items-center px-4 py-2 bg-gradient-to-r from-green-600 to-green-700 text-white rounded-lg hover:from-green-700 hover:to-green-800 transition-all duration-200 shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
              >
                <Download className="w-4 h-4 mr-2 group-hover:scale-110 transition-transform duration-200" />
                <span className="font-medium text-sm">Download</span>
              </button>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-100 rounded-lg transition-all duration-200 hover:shadow-md"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
          </div>
        )}

        {/* Tab Navigation - Fixed Header */}
        {!fullscreen && !transcript.accepted && (
          <div className="bg-gradient-to-r from-gray-50 to-gray-100 p-1 border-b border-gray-200 flex-shrink-0">
            {/* <nav className="flex space-x-2 bg-white rounded-xl p-1 shadow-sm"> */}
            <div className="flex w-full bg-gray-100 rounded-xl ">
              <button
                onClick={() => setActiveTab("player")}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-sm font-medium transition-all
      ${
        activeTab === "player"
          ? "bg-white shadow-sm text-blue-600 border-2 border-blue-600"
          : "text-gray-600 hover:text-gray-800"
      }`}
              >
                <Play className="w-4 h-4" />
                Media Player
              </button>

              <button
                onClick={() => setActiveTab("file")}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-sm font-medium transition-all
      ${
        activeTab === "file"
          ? "bg-white shadow-sm text-blue-600 border-2 border-blue-600"
          : "text-gray-600 hover:text-gray-800"
      }`}
              >
                <FileText className="w-4 h-4" />
                File Information
              </button>

              <button
                onClick={() => setActiveTab("transcription")}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-sm font-medium transition-all
      ${
        activeTab === "transcription"
          ? "bg-white shadow-sm text-blue-600 border-2 border-blue-600"
          : "text-gray-600 hover:text-gray-800"
      }`}
              >
                <BarChart3 className="w-4 h-4" />
                Transcription Info
              </button>
            </div>
            {/* <button
                onClick={() => setActiveTab('player')}
                className={`flex-1 flex items-center justify-center py-3 px-4 rounded-lg font-medium text-sm transition-all duration-200 ${
                  activeTab === 'player'
                    ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-md'
                    : 'text-gray-600 hover:text-gray-800 hover:bg-gradient-to-r hover:from-gray-50 hover:to-gray-100'
                }`}
              >
                <Play className={`w-4 h-4 mr-2 transition-colors duration-200 ${
                  activeTab === 'player' ? 'text-white' : 'text-gray-500 group-hover:text-gray-600'
                }`} />
                Media Player
              </button>
              
              <button
                onClick={() => setActiveTab('file')}
                className={`flex-1 flex items-center justify-center py-3 px-4 rounded-lg font-medium text-sm transition-all duration-200 ${
                  activeTab === 'file'
                    ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-md'
                    : 'text-gray-600 hover:text-gray-800 hover:bg-gradient-to-r hover:from-gray-50 hover:to-gray-100'
                }`}
              >
                <FileText className={`w-4 h-4 mr-2 transition-colors duration-200 ${
                  activeTab === 'file' ? 'text-white' : 'text-gray-500 group-hover:text-gray-600'
                }`} />
                File Information
              </button>
              
              <button
                onClick={() => setActiveTab('transcription')}
                className={`flex-1 flex items-center justify-center py-3 px-4 rounded-lg font-medium text-sm transition-all duration-200 ${
                  activeTab === 'transcription'
                    ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-md'
                    : 'text-gray-600 hover:text-gray-800 hover:bg-gradient-to-r hover:from-gray-50 hover:to-gray-100'
                }`}
              >
                <BarChart3 className={`w-4 h-4 mr-2 transition-colors duration-200 ${
                  activeTab === 'transcription' ? 'text-white' : 'text-gray-500 group-hover:text-gray-600'
                }`} />
                Transcription Info
              </button> */}
            {/* </nav> */}
          </div>
        )}

        {/* Tab Content Area - Scrollable */}
        <div className="flex-1 overflow-hidden">
          {activeTab === "player" && !transcript.accepted && (
            <div
              className={`flex ${
                fullscreen ? "h-full" : "h-96"
              } lg:h-[500px] p-4`}
            >
              {/* Media Player */}
              <div
                className={`${
                  fullscreen ? "w-full" : "w-1/2"
                } bg-black flex items-center justify-center relative`}
              >
                {isVideo ? (
                  <video
                    ref={mediaRef as React.RefObject<HTMLVideoElement>}
                    src={transcript.fileUrl}
                    className="w-full h-full object-contain"
                    onPlay={() => setPlaying(true)}
                    onPause={() => setPlaying(false)}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-900 to-purple-900">
                    <div className="text-center">
                      <div className="w-32 h-32 bg-white bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-6">
                        <Volume2 className="w-16 h-16 text-white" />
                      </div>
                      <h3 className="text-2xl font-bold text-white mb-2">
                        {transcript.fileName}
                      </h3>
                      <p className="text-white opacity-75">Audio Playback</p>
                    </div>
                    <audio
                      ref={mediaRef as React.RefObject<HTMLAudioElement>}
                      src={transcript.fileUrl}
                      onPlay={() => setPlaying(true)}
                      onPause={() => setPlaying(false)}
                    />
                  </div>
                )}
              </div>

              {/* Subtitles Panel */}
              {!fullscreen && (
                <div className="w-[500px] border-l border-gray-200 flex flex-col">
                  <div className="p-4 border-b border-gray-200 bg-gray-50">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold text-gray-900">Subtitles</h3>
                      <span className="text-xs text-gray-500 bg-gray-200 px-2 py-1 rounded-full">
                        {filteredSubtitles.length}/{subtitles.length}
                      </span>
                    </div>
                    <div className="relative">
                      <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                      <input
                        type="text"
                        placeholder="Search subtitles..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-2">
                    {filteredSubtitles.map((subtitle) => (
                      <div
                        key={subtitle.id}
                        className={`p-3 rounded-lg transition-colors ${
                          activeSubtitle?.id === subtitle.id
                            ? "bg-blue-100 border border-blue-200"
                            : "bg-gray-50 hover:bg-gray-100 border border-transparent"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-gray-500">
                            {formatTime(subtitle.startTime)} -{" "}
                            {formatTime(subtitle.endTime)}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              // Handle edit functionality here
                              console.log("Edit subtitle:", subtitle.id);
                            }}
                            className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Edit subtitle"
                          >
                            <Edit className="w-3 h-3" />
                          </button>
                        </div>
                        <div
                          onClick={() => jumpToSubtitle(subtitle)}
                          className="cursor-pointer"
                        >
                          <p className="text-sm text-gray-900">
                            {subtitle.text}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "file" && !transcript.accepted && (
            <div className="p-6 pb-8 overflow-y-auto">
              <div className="bg-white rounded-lg border border-gray-200">
                <div className="p-6 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <FileText className="w-5 h-5 mr-2" />
                    File Information
                  </h3>
                </div>
                <div className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          File Name
                        </label>
                        <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">
                          {transcript.fileName}
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          File Type
                        </label>
                        <p className="text-gray-900 bg-gray-50 p-3 rounded-lg capitalize">
                          {transcript.fileType}
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          File Size
                        </label>
                        <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">
                          {(Math.random() * 50 + 10).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Status
                        </label>
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                          Completed
                        </span>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Duration
                        </label>
                        <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">
                          {formatTime(duration)}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "transcription" && !transcript.accepted && (
            <div className="p-6 pb-8 overflow-y-auto">
              <div className="bg-white rounded-lg border border-gray-200">
                <div className="p-6 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <BarChart3 className="w-5 h-5 mr-2" />
                    Transcription Information
                  </h3>
                </div>
                <div className="p-6 space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Processing Time
                        </label>
                        <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">
                          {(Math.random() * 10 + 2).toFixed(1)} minutes
                        </p>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Accuracy Score
                        </label>
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-gray-900">
                              {(Math.random() * 20 + 80).toFixed(1)}%
                            </span>
                            <span className="text-sm text-gray-500">High</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-green-500 h-2 rounded-full"
                              style={{ width: `${Math.random() * 20 + 80}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Confidence Level
                        </label>
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-gray-900">
                              {(Math.random() * 15 + 85).toFixed(1)}%
                            </span>
                            <span className="text-sm text-gray-500">
                              Very High
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-500 h-2 rounded-full"
                              style={{ width: `${Math.random() * 15 + 85}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Accepted Transcript View */}
          {transcript.accepted && (
            <div className="p-6 pb-8 overflow-y-auto">
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-green-50 to-emerald-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center mr-4">
                        <Check className="w-5 h-5 text-green-600" />
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold text-gray-900">
                          Accepted Transcript
                        </h3>
                        <p className="text-sm text-gray-600 mt-1">
                          This transcript has been accepted and is ready for
                          use.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
                        Ready
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h4 className="text-lg font-semibold text-gray-900 flex items-center">
                      <FileText className="w-5 h-5 mr-2 text-blue-600" />
                      SRT Subtitles
                    </h4>
                    <div className="flex items-center space-x-2 text-sm text-gray-500">
                      <span>
                        {filteredSubtitles.length}/{subtitles.length} segments
                      </span>
                      <span>•</span>
                      <span>{formatTime(duration)} duration</span>
                    </div>
                  </div>

                  <div className="mb-4">
                    <div className="relative">
                      <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                      <input
                        type="text"
                        placeholder="Search transcript content..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
                    <div className="bg-gray-100 px-4 py-3 border-b border-gray-200">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">
                          Transcript
                        </span>
                      </div>
                    </div>

                    <div className="max-h-96 overflow-y-auto">
                      {filteredSubtitles.map((subtitle, index) => (
                        <div
                          key={subtitle.id}
                          onClick={() => jumpToSubtitle(subtitle)}
                          className="p-4 border-b border-gray-200 hover:bg-white transition-colors cursor-pointer group last:border-b-0"
                        >
                          <div className="flex items-start mb-2">
                            <div className="flex items-center space-x-3">
                              <span className="w-6 h-6 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full flex items-center justify-center">
                                {index + 1}
                              </span>
                              <div className="flex items-center space-x-2">
                                <span className="text-xs font-mono text-gray-500 bg-gray-200 px-2 py-1 rounded">
                                  {formatSrtTime(subtitle.startTime)}
                                </span>
                                <span className="text-gray-400">→</span>
                                <span className="text-xs font-mono text-gray-500 bg-gray-200 px-2 py-1 rounded">
                                  {formatSrtTime(subtitle.endTime)}
                                </span>
                              </div>
                            </div>
                          </div>
                          <p className="text-gray-900 leading-relaxed pl-9">
                            {subtitle.text}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Controls - Only show for player tab */}
        {activeTab === "player" && !transcript.accepted && (
          <div className="p-6 bg-gradient-to-r from-gray-50 to-gray-100 border-t border-gray-200">
            <div className="flex items-center space-x-4">
              <button
                onClick={togglePlayback}
                className="group p-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-full hover:from-blue-700 hover:to-blue-800 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105"
              >
                {playing ? (
                  <Pause className="w-6 h-6" />
                ) : (
                  <Play className="w-6 h-6" />
                )}
              </button>

              <div className="flex-1 flex items-center space-x-4">
                <span className="text-sm font-medium text-gray-700 w-16 text-center">
                  {formatTime(currentTime)}
                </span>
                <div className="flex-1 relative">
                  <input
                    type="range"
                    min="0"
                    max={duration || 0}
                    value={currentTime}
                    onChange={handleSeek}
                    className="w-full h-3 bg-gray-200 rounded-full appearance-none cursor-pointer slider focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                    style={{
                      background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${
                        (currentTime / (duration || 1)) * 100
                      }%, #e5e7eb ${
                        (currentTime / (duration || 1)) * 100
                      }%, #e5e7eb 100%)`,
                    }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-700 w-16 text-center">
                  {formatTime(duration)}
                </span>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={toggleMute}
                  className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition-all duration-200"
                >
                  {muted ? (
                    <VolumeX className="w-5 h-5" />
                  ) : (
                    <Volume2 className="w-5 h-5" />
                  )}
                </button>
                <div className="flex items-center space-x-2">
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={muted ? 0 : volume}
                    onChange={handleVolumeChange}
                    className="w-20 h-2 bg-gray-200 rounded-full appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
                    style={{
                      background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${
                        (muted ? 0 : volume) * 100
                      }%, #e5e7eb ${
                        (muted ? 0 : volume) * 100
                      }%, #e5e7eb 100%)`,
                    }}
                  />
                </div>
              </div>

              <button
                onClick={toggleFullscreen}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition-all duration-200"
              >
                <Maximize2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TranscriptPlayer;
