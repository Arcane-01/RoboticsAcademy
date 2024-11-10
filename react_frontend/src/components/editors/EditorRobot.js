import * as React from "react";
import { Box } from "@mui/material";

import "../../styles/editors/EditorRobot.css";

// monaco editor import start
import "../../styles/tailwind.css";
import {
  MonacoEditor,
  defaultEditorSourceCode,
} from "./monaco-editor";
import { useEditorReudcer } from "../../hooks/useEditorReudcer";
// monaco editor import end

window.RoboticsReactComponents = window.RoboticsReactComponents || {};

window.RoboticsReactComponents.CodeEditor = (function () {
  let editorCode = "";
  const editorCodeChangeSuscribers = [];

  const setCode = (code) => {
    editorCode = code;
    for (
      let i = 0, length = editorCodeChangeSuscribers.length;
      i < length;
      ++i
    ) {
      editorCodeChangeSuscribers[i](code);
    }
  };

  const OnEditorCodeChanged = (handler) => {
    editorCodeChangeSuscribers.push(handler);
  };

  const getCode = () => editorCode;

  return {
    setCode: setCode,
    getCode: getCode,
    OnEditorCodeChanged: OnEditorCodeChanged,
  };
})();

export default function EditorRobot(props) {
  const [monacoEditorSourceCode, setMonacoEditorSourceCode] = React.useState(
    defaultEditorSourceCode
  );

  React.useEffect(() => {
    // monaco
    RoboticsReactComponents.CodeEditor.setCode(monacoEditorSourceCode);
    RoboticsReactComponents.CodeEditor.OnEditorCodeChanged((code) => {
      setMonacoEditorSourceCode(code);
    });

    const codeLoadedEvent = new CustomEvent("codeLoaded", {
      detail: { isLoading: false },
    });
    window.dispatchEvent(codeLoadedEvent);
  }, []);

  //! Monaco Code Editor

  const [state, dispatch] = useEditorReudcer();

  // monaco editor code change
  const handleMonacoEditorCodeChange = (code) => {
    setMonacoEditorSourceCode(code);
    RoboticsReactComponents.CodeEditor.setCode(code);
  };

  return (
    <Box id="code-container">
      <MonacoEditor
        state={state}
        dispatch={dispatch}
        monacoEditorSourceCode={monacoEditorSourceCode}
        setMonacoEditorSourceCode={setMonacoEditorSourceCode}
        handleMonacoEditorCodeChange={handleMonacoEditorCodeChange}
      />
    </Box>
  );
}
