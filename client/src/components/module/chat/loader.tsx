export default function Loader() {
  return Array.from({ length: 4 }).map((_, id) => {
    return (
      <div
        key={id}
        className="bg-neutral-100 dark:bg-light-100 flex w-full h-96 rounded-[12px]"
      />
    );
  });
}
