declare interface ITextArea {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  placeholder?: string;
  className?: string;
}

declare interface IChatInput {
  onSend: (message: string) => void;
  msg: string;
  setMsg: (msg: string) => void;
  placeholder?: string;
  className?: string;
  handleBack?: () => void;
  isBack?: boolean;
}

declare interface IAccordionData {
  value: string;
  title: string;
  content: string | React.ReactNode;
}

declare interface IAccordion {
  items: IAccordionData[];
  type?: "single";
  collapsible?: boolean;
  className?: string;
  defaultValue?: string;
}
