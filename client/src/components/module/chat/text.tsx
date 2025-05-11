export default function Result({ item }: { item: IPrompt }) {
  const name = item.duck_name;
  return (
    <div className="bg-neutral-100 dark:bg-light-100 p-4 flex w-full min-h-96 rounded-[12px] flex flex-col gap-[12px]">
      <div className="flex items-center gap-[8px]">
        <img
          src={
            item.images?.startsWith("https")
              ? item.images
              : "src/assets/react.svg"
          }
          alt={name}
          className="rounded-full min-w-[50px] h-[50px] object-cover object-center"
        />
        <span className="flex items-center gap-[8px] *:font-semibold *:text-base">
          <p>{name}</p>
          <p>({item.score})</p>
        </span>
      </div>
      <p>{item.reasoning}</p>
    </div>
  );
}
