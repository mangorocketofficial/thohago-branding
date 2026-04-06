(function () {
  const panel = document.getElementById("voice-answer-panel");
  if (!panel) {
    return;
  }

  const startButton = document.getElementById("start-recording");
  const stopButton = document.getElementById("stop-recording");
  const recordingIndicator = document.getElementById("recording-indicator");
  const statusBox = document.getElementById("voice-status");
  const textForm = document.getElementById("text-answer-form");
  const textArea = document.getElementById("answer-textarea");
  const eventsUrl = panel.dataset.eventsUrl;
  const recordUrl = panel.dataset.recordUrl;
  const retryUrl = panel.dataset.retryUrl;
  let autoSubmitTranscript = panel.dataset.isConfirming !== "true";
  let needsRetryBeforeRecording = panel.dataset.isConfirming === "true";

  let mediaRecorder = null;
  let chunks = [];
  let mediaStream = null;

  function setStatus(message, tone) {
    if (!statusBox) {
      return;
    }
    statusBox.textContent = message;
    statusBox.classList.remove("error", "success");
    if (tone === "error") {
      statusBox.classList.add("error");
    }
    if (tone === "success") {
      statusBox.classList.add("success");
    }
  }

  function setRecordingState(isRecording) {
    if (recordingIndicator) {
      recordingIndicator.classList.toggle("is-hidden", !isRecording);
    }
    if (startButton) {
      startButton.classList.toggle("is-hidden", isRecording);
      startButton.disabled = false;
    }
    if (stopButton) {
      stopButton.classList.toggle("is-hidden", !isRecording);
      stopButton.disabled = !isRecording;
    }
  }

  function submitTranscript(text) {
    if (!textForm || !textArea) {
      return;
    }
    textArea.value = text;
    textForm.submit();
  }

  const eventSource = new EventSource(eventsUrl);
  eventSource.addEventListener("transcribing", function () {
    setStatus("녹음 내용을 전사하고 있어요.", null);
  });
  eventSource.addEventListener("transcript_ready", function (event) {
    const payload = JSON.parse(event.data);
    if (!autoSubmitTranscript) {
      setStatus("답변내용이 준비되었어요. 확인 후 다음 단계로 넘어가세요.", "success");
      return;
    }
    setStatus("전사가 완료되어 답변 확인 단계로 이동합니다.", "success");
    submitTranscript(payload.text || "");
  });
  eventSource.addEventListener("transcript_failed", function (event) {
    const payload = JSON.parse(event.data);
    setRecordingState(false);
    setStatus(payload.error || "전사에 실패했어요. 다시 녹음하거나 직접 입력해 주세요.", "error");
  });

  async function ensureRecorder() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
      throw new Error("이 브라우저에서는 음성 녹음을 사용할 수 없어요.");
    }

    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
    mediaRecorder = new MediaRecorder(mediaStream, mimeType ? { mimeType } : undefined);

    mediaRecorder.addEventListener("dataavailable", function (event) {
      if (event.data && event.data.size > 0) {
        chunks.push(event.data);
      }
    });

    mediaRecorder.addEventListener("stop", async function () {
      const blob = new Blob(chunks, { type: mediaRecorder.mimeType || "audio/webm" });
      chunks = [];
      setRecordingState(false);
      setStatus("녹음을 업로드하고 있어요.", null);

      const formData = new FormData();
      formData.append("audio", blob, "turn_audio.webm");

      try {
        const response = await fetch(recordUrl, {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || "음성 업로드에 실패했어요.");
        }
      } catch (error) {
        setStatus(error.message || "음성 업로드에 실패했어요.", "error");
      } finally {
        if (mediaStream) {
          mediaStream.getTracks().forEach(function (track) {
            track.stop();
          });
          mediaStream = null;
        }
        mediaRecorder = null;
      }
    });
  }

  async function startRecordingFlow() {
    try {
      autoSubmitTranscript = true;
      setRecordingState(true);
      setStatus("녹음 중입니다.", null);
      chunks = [];
      await ensureRecorder();
      mediaRecorder.start();
    } catch (error) {
      setRecordingState(false);
      setStatus(error.message || "녹음을 시작할 수 없어요.", "error");
    }
  }

  if (startButton) {
    startButton.addEventListener("click", async function () {
      try {
        if (needsRetryBeforeRecording) {
          const response = await fetch(retryUrl, { method: "POST" });
          if (!response.ok) {
            throw new Error("기존 답변을 새 녹음 상태로 바꾸지 못했어요.");
          }
          needsRetryBeforeRecording = false;
        }
        await startRecordingFlow();
      } catch (error) {
        setRecordingState(false);
        setStatus(error.message || "녹음을 시작할 수 없어요.", "error");
      }
    });
  }

  if (stopButton) {
    stopButton.addEventListener("click", function () {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
    });
  }
})();
