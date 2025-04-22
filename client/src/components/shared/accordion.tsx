import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export function CAccordion({
  items,
  type = "single",
  collapsible = true,
  className = "w-full",
  defaultValue,
}: IAccordion) {
  return (
    <Accordion
      type={type}
      collapsible={collapsible}
      className={className}
      defaultValue={defaultValue}
    >
      {items.map(({ value, title, content }) => (
        <AccordionItem key={value} value={value}>
          <AccordionTrigger className="font-semibold">{title}</AccordionTrigger>
          <AccordionContent>{content}</AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
