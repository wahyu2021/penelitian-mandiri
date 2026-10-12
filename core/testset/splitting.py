"""Pembagian kelompok set uji (stratified split) dengan pencegahan kebocoran data (anti-leak)."""
import hashlib
import random
from collections import defaultdict
from typing import Dict, List, Set, Tuple


def compute_content_sha256(content: str) -> str:
    """Hitung SHA-256 string konten."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def find_connected_query_clusters(
    queries: List[Dict[str, object]],
) -> List[List[Dict[str, object]]]:
    """Kelompokkan kueri yang berbagi SPM sama, arsip asal sama, atau kemiripan identik.

    Semua kueri dalam satu klaster wajib masuk kelompok (split) yang sama
    agar tidak terjadi kebocoran informasi antar kelompok tuning dan test.
    """
    spm_to_qidx: Dict[str, Set[int]] = defaultdict(set)
    arch_to_qidx: Dict[int, Set[int]] = defaultdict(set)

    for idx, q in enumerate(queries):
        spm = str(q.get("spm_number") or "").strip().upper()
        if spm:
            spm_to_qidx[spm].add(idx)
        orig_id = q.get("origin_archive_id")
        if orig_id is not None:
            arch_to_qidx[int(orig_id)].add(idx)

    # Buat adjacency graph antar indeks kueri
    adj: Dict[int, Set[int]] = defaultdict(set)
    for qindices in spm_to_qidx.values():
        q_list = list(qindices)
        for i in range(len(q_list)):
            for j in range(i + 1, len(q_list)):
                adj[q_list[i]].add(q_list[j])
                adj[q_list[j]].add(q_list[i])

    for qindices in arch_to_qidx.values():
        q_list = list(qindices)
        for i in range(len(q_list)):
            for j in range(i + 1, len(q_list)):
                adj[q_list[i]].add(q_list[j])
                adj[q_list[j]].add(q_list[i])

    visited: Set[int] = set()
    clusters: List[List[Dict[str, object]]] = []

    for i in range(len(queries)):
        if i not in visited:
            component = []
            queue = [i]
            visited.add(i)
            while queue:
                curr = queue.pop(0)
                component.append(queries[curr])
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            clusters.append(component)

    return clusters


def split_queries_stratified_anti_leak(
    queries: List[Dict[str, object]],
    tuning_ratio: float = 0.30,
    seed: int = 42,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    """Bagi kueri menjadi kelompok tuning (~30%) dan test (~70%) berstrata anti-leak.

    Args:
        queries: Daftar kamus kueri.
        tuning_ratio: Proporsi kelompok tuning (default: 0.30).
        seed: Random seed untuk pembagian deterministik.

    Returns:
        Pasangan (tuning_queries, test_queries).
    """
    clusters = find_connected_query_clusters(queries)
    rng = random.Random(seed)

    # Kelompokkan klaster berdasarkan stratum (source + query_type klaster)
    strata: Dict[str, List[List[Dict[str, object]]]] = defaultdict(list)
    for c in clusters:
        # Gunakan atribut kueri pertama di klaster sebagai representasi stratum
        rep = c[0]
        s_key = f"{rep.get('source', 'sintetis')}|{rep.get('query_type', 'umum')}"
        strata[s_key].append(c)

    tuning_clusters: List[List[Dict[str, object]]] = []
    test_clusters: List[List[Dict[str, object]]] = []

    for _, c_list in strata.items():
        shuffled = list(c_list)
        rng.shuffle(shuffled)
        total_q_in_stratum = sum(len(c) for c in shuffled)
        target_tuning_q = int(round(total_q_in_stratum * tuning_ratio))

        curr_tuning_q = 0
        for c in shuffled:
            if curr_tuning_q + len(c) <= target_tuning_q and curr_tuning_q < target_tuning_q:
                tuning_clusters.append(c)
                curr_tuning_q += len(c)
            else:
                test_clusters.append(c)

    tuning_queries = [q for c in tuning_clusters for q in c]
    test_queries = [q for c in test_clusters for q in c]

    # Tandai atribut split pada masing-masing kueri
    for q in tuning_queries:
        q["split"] = "tuning"
    for q in test_queries:
        q["split"] = "test"

    return tuning_queries, test_queries
