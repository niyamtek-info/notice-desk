import { Modal, Progress, Button } from "antd";
import { useEffect, useRef, useState } from "react";
import { GoCheckCircleFill } from "react-icons/go";
import { DocumentApi } from "@/src/services/DocumentApi";

interface ProgressModelProps {
  fileId: string;
  open: boolean;
  setOpen: (open: boolean) => void;
  trigger: any;
  setTrigger: (triger: number) => void;
}

const ProgressModel = ({
  fileId,
  open,
  setOpen,
  trigger,
  setTrigger,
}: ProgressModelProps) => {
  const [progress, setProgress] = useState<number | null>(0);
  const [progressStage, setProgressStage] = useState<string>("");
  const isStoppedRef = useRef(false);

  useEffect(() => {
    if (!fileId || isStoppedRef.current) return;

    let cancelled = false;

    const pollProgress = async () => {
      try {
        const progressData = await DocumentApi.documentProgressGetApi(fileId);
        if (cancelled) {
          return;
        }

        const percent = progressData?.progress ?? 0;
        const stage = progressData?.stage ?? "";
        const status = String(progressData?.status ?? "").toLowerCase();

        setProgress(percent);
        setProgressStage(stage);

        if (
          percent >= 100 ||
          status === "completed" ||
          status === "failed" ||
          stage.toLowerCase().includes("failed")
        ) {
          window.clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Error fetching progress data:", error);
      }
    };

    pollProgress();
    const intervalId = window.setInterval(pollProgress, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [fileId]);

  return (
    <>
      <Modal
        open={open}
        footer={null}
        closable={false}
        maskClosable={false}
        centered
        styles={{
          mask: {
            backgroundColor: "rgba(0,0,0,0.6)",
          },
        }}
      >
        <div className="flex flex-col items-center justify-center py-8 px-4">
          {progress === 100 ? (
            <div className="flex flex-col items-center animate-in fade-in zoom-in duration-300">
              <GoCheckCircleFill className="text-green-500 text-[70px] mb-4 shadow-sm rounded-full" />
              <p className="text-xl font-semibold text-gray-800 mb-2">
                Completed Successfully!
              </p>
              <p className="text-sm text-gray-500 text-center max-w-[250px]">
                Your document has been processed and is ready for review.
              </p>
            </div>
          ) : (
            <>
              <Progress
                type="circle"
                percent={progress || 0}
                strokeColor={{ "0%": "#108ee9", "100%": "#87d068" }}
                strokeWidth={8}
              />
              <p className="mt-6 text-lg font-medium text-gray-700">
                {progressStage || "Starting process"}...
              </p>
              <p className="text-sm text-gray-400 mt-2">
                Please wait while we analyze your document
              </p>
            </>
          )}

          {progress === 100 && (
            <Button
              type="primary"
              size="large"
              className="mt-8 bg-green-500 hover:bg-green-600 border-none px-8 h-10 rounded-lg shadow-md font-medium"
              onClick={() => {
                setOpen(false);
                setTrigger(trigger + 1);
              }}
            >
              Done
            </Button>
          )}
        </div>
      </Modal>
    </>
  );
};

export default ProgressModel;
