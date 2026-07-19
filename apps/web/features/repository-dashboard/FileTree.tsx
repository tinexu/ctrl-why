import type { SourceFile } from "@/lib/repository-types";

import styles from "./dashboard.module.css";

type TreeItem = {
  name: string;
  path: string;
  file?: SourceFile;
  children: Map<string, TreeItem>;
};

function buildTree(files: SourceFile[]): TreeItem {
  const root: TreeItem = { name: "", path: "", children: new Map() };
  for (const file of files) {
    let current = root;
    const parts = file.path.split("/");
    parts.forEach((part, index) => {
      const path = parts.slice(0, index + 1).join("/");
      if (!current.children.has(part)) {
        current.children.set(part, { name: part, path, children: new Map() });
      }
      current = current.children.get(part)!;
      if (index === parts.length - 1) current.file = file;
    });
  }
  return root;
}

function TreeBranch({ item, depth }: { item: TreeItem; depth: number }) {
  const children = [...item.children.values()].sort((left, right) => {
    const leftFolder = left.children.size > 0 && !left.file;
    const rightFolder = right.children.size > 0 && !right.file;
    if (leftFolder !== rightFolder) return leftFolder ? -1 : 1;
    return left.name.localeCompare(right.name);
  });
  if (item.file) {
    return (
      <li className={styles.file} style={{ paddingLeft: `${depth * 0.8}rem` }} title={item.file.path}>
        <span className={styles.fileDot} data-language={item.file.language} />
        <span>{item.name}</span>
        <span className={styles.fileLines}>{item.file.line_count}</span>
      </li>
    );
  }
  return (
    <li>
      {item.name && (
        <details open={depth < 2}>
          <summary className={styles.folder} style={{ paddingLeft: `${Math.max(0, depth - 1) * 0.8}rem` }}>
            {item.name}
          </summary>
          <ul className={styles.treeList}>{children.map((child) => <TreeBranch key={child.path} item={child} depth={depth + 1} />)}</ul>
        </details>
      )}
      {!item.name && <ul className={styles.treeList}>{children.map((child) => <TreeBranch key={child.path} item={child} depth={0} />)}</ul>}
    </li>
  );
}

export function FileTree({ files }: { files: SourceFile[] }) {
  return <TreeBranch item={buildTree(files)} depth={0} />;
}

