# Benchmark Per-Reference Report

Generated at (UTC): `2026-02-22T16:42:53.633459+00:00`

## Scoring Policy

- Primary: `mutation-correction rate (targeted wrong fields fixed / targeted wrong fields)`
- Targeted Fields Source: `manifest.mutated_fields_core with auto-diff fallback`
- Core Fields: `['title', 'authors', 'journal', 'doi', 'year', 'url']`

## Overall Summary

- Threshold: `0.8`
- Correction: `33` / `37` = `0.891892`
- Average status score: `0.171429`
- Total citations: `14`
- Passed: `True`

## File Summaries

- TEX: fixed `17` / `19` = `0.894737` | avg_status=`0.171429`
- TXT: fixed `16` / `18` = `0.888889` | avg_status=`0.171429`

## TEX Citations

### TEX `paper:1`

Status: `status=critical_mismatch` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=None` | `recommended_candidate_rank=1`

Correction Summary: `targeted=5` | `fixed=4` | `correction_rate=0.8` | `targeted_source=manifest` | `status_score=0.0`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Halil Savuran<br>Murat Karakaya | Halil Savuran<br>Murat Karakaya | Halil Savuran<br>Murat Karakaya | 1 | 1 | Not Needed |
| `title` | yes | A novel solution for routeing a swarm of drones operated on a mobile host | A novel solution for routing a swarm of drones operated on a mobile host | A novel solution for routing a swarm of drones operated on a mobile host | 0 | 1 | yes |
| `journal` | yes | '' Engineering Applications of Artificial Intelligence 139, 109337 (2025) | '' Engineering Applications of Artificial Intelligence 139, 109337 (2025) | '' Engineering Applications of Artificial Intelligence 138, 109337 (2024) | 0 | 0 | no |
| `volume` | n/a | `<null>` | 138 | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | 109337 | `<null>` | n/a | n/a | n/a |
| `year` | yes | 2025 | 2024 | 2024 | 0 | 1 | yes |
| `doi` | yes | `<null>` | 10.1016/j.engappai.2024.109337 | 10.1016/j.engappai.2024.109337 | 0 | 1 | yes |
| `url` | yes | `<null>` | https://doi.org/10.1016/j.engappai.2024.109337 | https://doi.org/10.1016/j.engappai.2024.109337 | 0 | 1 | yes |

### TEX `paper:2`

Status: `status=critical_mismatch` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=1` | `recommended_candidate_rank=1`

Correction Summary: `targeted=4` | `fixed=4` | `correction_rate=1.0` | `targeted_source=manifest` | `status_score=0.0`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | yes | Gökhan Şengül, Murat Karakaya, Olusola O. Abayomi-Alli,<br>Robertas Damaševičius | Gökhan Şengül<br>Murat Karakaya<br>Sanjay Misra<br>Olusola O. Abayomi-Alli<br>Robertas Damaševičius | Gökhan Şengül, Murat Karakaya, Sanjay Misra, Olusola O. Abayomi-Alli,<br>Robertas Damaševičius | 0.888889 | 1 | yes |
| `title` | no | Deep learning based fall detection using smartwatches for healthcare applications | Deep learning based fall detection using smartwatches for healthcare applications | Deep learning based fall detection using smartwatches for healthcare applications | 1 | 1 | Not Needed |
| `journal` | no | '' Biomedical Signal Processing and Control 71, 103242 (2023) | '' Biomedical Signal Processing and Control 71, 103242 (2023) | '' Biomedical Signal Processing and Control 71, 103242 (2022) | 0 | 0 | Not Needed |
| `volume` | n/a | `<null>` | 71 | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | 103242 | `<null>` | n/a | n/a | n/a |
| `year` | yes | 2023 | 2022 | 2022 | 0 | 1 | yes |
| `doi` | yes | 10.9999/fake.fall.2023 | 10.1016/j.bspc.2021.103242 | 10.1016/j.bspc.2021.103242 | 0 | 1 | yes |
| `url` | yes | https://doi.org/10.9999/fake.fall.2023 | https://doi.org/10.1016/j.bspc.2021.103242 | https://doi.org/10.1016/j.bspc.2021.103242 | 0 | 1 | yes |

Warnings: `["auto_diff_only_fields=['journal']"]`

### TEX `paper:3`

Status: `status=critical_mismatch` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=1` | `recommended_candidate_rank=1`

Correction Summary: `targeted=2` | `fixed=2` | `correction_rate=1.0` | `targeted_source=manifest` | `status_score=0.0`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Tolga Üstünkök<br>Murat Karakaya | Tolga Üstünkök<br>Murat Karakaya | Tolga Üstünkök<br>Murat Karakaya | 1 | 1 | Not Needed |
| `title` | yes | SS-MLA: a semisupervised method for multi-label annotation | SS-MLA: a semisupervised method for multi-label annotation of remotely sensed images | SS-MLA: a semisupervised method for multi-label annotation of remotely sensed images | 0 | 1 | yes |
| `journal` | yes | '' Journal of Advanced Remote Sensing 15(03), 036509, 99(9), 999--1001 (2021) | Journal of Applied Remote Sensing | '' Journal of Applied Remote Sensing 15(03), 036509 (2021) | 0 | 1 | yes |
| `volume` | n/a | `<null>` | 15 | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | 03 | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `year` | no | 2021 | 2021 | 2021 | 1 | 1 | Not Needed |
| `doi` | no | 10.1117/1.JRS.15.036509 | 10.1117/1.JRS.15.036509 | 10.1117/1.JRS.15.036509 | 1 | 1 | Not Needed |
| `url` | no | https://doi.org/10.1117/1.JRS.15.036509 | https://doi.org/10.1117/1.JRS.15.036509 | https://doi.org/10.1117/1.JRS.15.036509 | 1 | 1 | Not Needed |

### TEX `paper:4`

Status: `status=unresolved` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=None` | `recommended_candidate_rank=None`

Correction Summary: `targeted=0` | `fixed=0` | `correction_rate=1.0` | `targeted_source=manifest` | `status_score=0.6`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Murat Karakaya, M. Eryilmaz,<br>U. O. Ceyhan | Murat Karakaya, M. Eryilmaz,<br>U. O. Ceyhan | Murat Karakaya, M. Eryilmaz,<br>U. O. Ceyhan | 1 | 1 | Not Needed |
| `title` | no | Analyzing students Academic Success in Prerequisite Course Chains | Analyzing students Academic Success in Prerequisite Course Chains | Analyzing students' Academic Success in Prerequisite Course Chains | 1 | 1 | Not Needed |
| `journal` | no | '' International Journal of Engineering Education 34(2A), 364--376 (2018) | '' International Journal of Engineering Education 34(2A), 364--376 (2018) | '' International Journal of Engineering Education 34(2A), 364--370 (2018) | 0 | 0 | Not Needed |
| `volume` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `year` | no | 2018 | 2018 | 2018 | 1 | 1 | Not Needed |
| `doi` | no | 10.4242/fake.chain.2018 | 10.4242/fake.chain.2018 | `<null>` | 0 | 0 | Not Needed |
| `url` | no | https://doi.org/10.4242/fake.chain.2018 | https://doi.org/10.4242/fake.chain.2018 | `<null>` | 0 | 0 | Not Needed |

Warnings: `["auto_diff_only_fields=['journal']"]`

### TEX `paper:5`

Status: `status=critical_mismatch` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=1` | `recommended_candidate_rank=1`

Correction Summary: `targeted=4` | `fixed=4` | `correction_rate=1.0` | `targeted_source=manifest` | `status_score=0.0`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Halil Savuran<br>Murat Karakaya | Halil Savuran<br>Murat Karakaya | Halil Savuran<br>Murat Karakaya | 1 | 1 | Not Needed |
| `title` | yes | Efficient route planning for an unmanned air vehicle deployed on a stationary carrier | Efficient route planning for an unmanned air vehicle deployed on a moving carrier | Efficient route planning for an unmanned air vehicle deployed on a moving carrier | 0 | 1 | yes |
| `journal` | no | '' Soft Computing 20(7), 2905--2920 (2017) | '' Soft Computing 20(7), 2905--2920 (2017) | '' Soft Computing 20(7), 2905--2920 (2016) | 0 | 0 | Not Needed |
| `volume` | n/a | `<null>` | 20 | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | 7 | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | 2905-2920 | `<null>` | n/a | n/a | n/a |
| `year` | yes | 2017 | 2016 | 2016 | 0 | 1 | yes |
| `doi` | yes | 10.1007/s00500-015-1970-9 | 10.1007/s00500-015-1970-4 | 10.1007/s00500-015-1970-4 | 0 | 1 | yes |
| `url` | yes | https://doi.org/10.1007/s00500-015-1970-9 | https://doi.org/10.1007/s00500-015-1970-4 | https://doi.org/10.1007/s00500-015-1970-4 | 0 | 1 | yes |

Warnings: `["auto_diff_only_fields=['journal']"]`

### TEX `paper:6`

Status: `status=critical_mismatch` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=1` | `recommended_candidate_rank=1`

Correction Summary: `targeted=4` | `fixed=3` | `correction_rate=0.75` | `targeted_source=manifest` | `status_score=0.0`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Murat Karakaya | Murat Karakaya | Murat Karakaya | 1 | 1 | Not Needed |
| `title` | yes | An Efficient Data Collection Heuristic for Wireless Sensor Networks with Limited Sensor Memory Capacity | MSCT: An Efficient Data Collection Heuristic for Wireless Sensor Networks with Limited Sensor Memory Capacity | MSCT: An Efficient Data Collection Heuristic for Wireless Sensor Networks with Limited Sensor Memory Capacity | 0 | 1 | yes |
| `journal` | yes | '' KSII Transactions on Internet and Information Systems 9(4), 3396--3411 (2015) | '' KSII Transactions on Internet and Information Systems 9(4), 3396--3411 (2015) | '' KSII Transactions on Internet and Information Systems 9(9), 3396--3411 (2015) | 0 | 0 | no |
| `volume` | n/a | `<null>` | 9 | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | 9 | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `year` | no | 2015 | 2015 | 2015 | 1 | 1 | Not Needed |
| `doi` | yes | `<null>` | 10.3837/tiis.2015.09.007 | 10.3837/tiis.2015.09.007 | 0 | 1 | yes |
| `url` | yes | https://example.com/fake/msct | https://doi.org/10.3837/tiis.2015.09.007 | https://doi.org/10.3837/tiis.2015.09.007 | 0 | 1 | yes |

### TEX `paper:7`

Status: `status=unresolved` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=None` | `recommended_candidate_rank=None`

Correction Summary: `targeted=0` | `fixed=0` | `correction_rate=1.0` | `targeted_source=manifest` | `status_score=0.6`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Murat Karakaya | Murat Karakaya | Murat Karakaya | 1 | 1 | Not Needed |
| `title` | no | Time-Sensitive Ant Colony Optimization to Schedule a Mobile Sink for Data Collection in Wireless Sensor Networks | Time-Sensitive Ant Colony Optimization to Schedule a Mobile Sink for Data Collection in Wireless Sensor Networks | Time-Sensitive Ant Colony Optimization to Schedule a Mobile Sink for Data Collection in Wireless Sensor Networks | 1 | 1 | Not Needed |
| `journal` | no | '' Ad Hoc \& Sensor Wireless Networks 28(1--2), 65--92 (2015). \end{thebibliography} | '' Ad Hoc \& Sensor Wireless Networks 28(1--2), 65--92 (2015). \end{thebibliography} | '' Ad Hoc \& Sensor Wireless Networks 28(1--2), 65--82 (2015). No reliable Crossref match found; DOI unavailable. \end{thebibliography} | 0 | 0 | Not Needed |
| `volume` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `year` | no | 2015 | 2015 | 2015 | 1 | 1 | Not Needed |
| `doi` | no | 10.5555/ahsn.2015.028 | 10.5555/ahsn.2015.028 | `<null>` | 0 | 0 | Not Needed |
| `url` | no | https://doi.org/10.5555/ahsn.2015.028 | https://doi.org/10.5555/ahsn.2015.028 | `<null>` | 0 | 0 | Not Needed |

Warnings: `["auto_diff_only_fields=['journal']"]`

## TXT Citations

### TXT `txt:1`

Status: `status=critical_mismatch` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=1` | `recommended_candidate_rank=1`

Correction Summary: `targeted=5` | `fixed=4` | `correction_rate=0.8` | `targeted_source=manifest` | `status_score=0.0`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Halil Savuran, Murat Karakaya | Halil Savuran<br>Murat Karakaya | Halil Savuran, Murat Karakaya | 1 | 1 | Not Needed |
| `title` | yes | A novel solution for routeing a swarm of drones operated on a mobile host | A novel solution for routing a swarm of drones operated on a mobile host | A novel solution for routing a swarm of drones operated on a mobile host | 0 | 1 | yes |
| `journal` | yes | ". '' Engineering Applications of Artificial Intelligence 139, 109337 (2025), 139, 109337 (2025) | ". '' Engineering Applications of Artificial Intelligence 139, 109337 (2025), 139, 109337 (2025) | ". '' Engineering Applications of Artificial Intelligence 138, 109337 (2024), 138, 109337 (2024) | 0 | 0 | no |
| `volume` | n/a | `<null>` | 138 | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | 109337 | `<null>` | n/a | n/a | n/a |
| `year` | yes | 2025 | 2024 | 2024 | 0 | 1 | yes |
| `doi` | yes | `<null>` | 10.1016/j.engappai.2024.109337 | 10.1016/j.engappai.2024.109337 | 0 | 1 | yes |
| `url` | yes | `<null>` | https://doi.org/10.1016/j.engappai.2024.109337 | https://doi.org/10.1016/j.engappai.2024.109337 | 0 | 1 | yes |

### TXT `txt:2`

Status: `status=critical_mismatch` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=1` | `recommended_candidate_rank=1`

Correction Summary: `targeted=4` | `fixed=4` | `correction_rate=1.0` | `targeted_source=manifest` | `status_score=0.0`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | yes | Gökhan Şengül, Murat Karakaya, Olusola O. Abayomi-Alli, Robertas Damaševičius | Gökhan Şengül<br>Murat Karakaya<br>Sanjay Misra<br>Olusola O. Abayomi-Alli<br>Robertas Damaševičius | Gökhan Şengül, Murat Karakaya, Sanjay Misra, Olusola O. Abayomi-Alli, Robertas Damaševičius | 0.888889 | 1 | yes |
| `title` | no | Deep learning based fall detection using smartwatches for healthcare applications | Deep learning based fall detection using smartwatches for healthcare applications | Deep learning based fall detection using smartwatches for healthcare applications | 1 | 1 | Not Needed |
| `journal` | no | ". '' Biomedical Signal Processing and Control 71, 103242 (2023), 71, 103242 (2023) | ". '' Biomedical Signal Processing and Control 71, 103242 (2023), 71, 103242 (2023) | ". '' Biomedical Signal Processing and Control 71, 103242 (2022), 71, 103242 (2022) | 0 | 0 | Not Needed |
| `volume` | n/a | `<null>` | 71 | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | 103242 | `<null>` | n/a | n/a | n/a |
| `year` | yes | 2023 | 2022 | 2022 | 0 | 1 | yes |
| `doi` | yes | 10.9999/fake.fall.2023 | 10.1016/j.bspc.2021.103242 | 10.1016/j.bspc.2021.103242 | 0 | 1 | yes |
| `url` | yes | https://doi.org/10.9999/fake.fall.2023 | https://doi.org/10.1016/j.bspc.2021.103242 | https://doi.org/10.1016/j.bspc.2021.103242 | 0 | 1 | yes |

Warnings: `["auto_diff_only_fields=['journal']"]`

### TXT `txt:3`

Status: `status=critical_mismatch` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=1` | `recommended_candidate_rank=1`

Correction Summary: `targeted=2` | `fixed=2` | `correction_rate=1.0` | `targeted_source=manifest` | `status_score=0.0`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Tolga Üstünkök, Murat Karakaya | Tolga Üstünkök<br>Murat Karakaya | Tolga Üstünkök, Murat Karakaya | 1 | 1 | Not Needed |
| `title` | yes | SS-MLA: a semisupervised method for multi-label annotation | SS-MLA: a semisupervised method for multi-label annotation of remotely sensed images | SS-MLA: a semisupervised method for multi-label annotation of remotely sensed images | 0 | 1 | yes |
| `journal` | yes | ". '' Journal of Advanced Remote Sensing 15(03), 036509 (2021), 15(03) (2021); 99(9), 999--1001 | Journal of Applied Remote Sensing | ". '' Journal of Applied Remote Sensing 15(03), 036509 (2021), 15(03) (2021) | 0 | 1 | yes |
| `volume` | n/a | `<null>` | 15 | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | 03 | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `year` | no | 2021 | 2021 | 2021 | 1 | 1 | Not Needed |
| `doi` | no | 10.1117/1.jrs.15.036509 | 10.1117/1.jrs.15.036509 | 10.1117/1.jrs.15.036509 | 1 | 1 | Not Needed |
| `url` | no | https://doi.org/10.1117/1.jrs.15.036509 | https://doi.org/10.1117/1.jrs.15.036509 | https://doi.org/10.1117/1.jrs.15.036509 | 1 | 1 | Not Needed |

### TXT `txt:4`

Status: `status=unresolved` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=None` | `recommended_candidate_rank=None`

Correction Summary: `targeted=0` | `fixed=0` | `correction_rate=1.0` | `targeted_source=manifest` | `status_score=0.6`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Murat Karakaya, M. Eryilmaz,<br>U. O. Ceyhan | Murat Karakaya, M. Eryilmaz,<br>U. O. Ceyhan | Murat Karakaya, M. Eryilmaz,<br>U. O. Ceyhan | 1 | 1 | Not Needed |
| `title` | no | Analyzing students Academic Success in Prerequisite Course Chains | Analyzing students Academic Success in Prerequisite Course Chains | Analyzing students' Academic Success in Prerequisite Course Chains | 1 | 1 | Not Needed |
| `journal` | no | ''International Journal of Engineering Education 34(2A), 364--376 (2018) | ''International Journal of Engineering Education 34(2A), 364--376 (2018) | ''International Journal of Engineering Education 34(2A), 364--370 (2018) | 0 | 0 | Not Needed |
| `volume` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `year` | no | 2018 | 2018 | 2018 | 1 | 1 | Not Needed |
| `doi` | no | 10.4242/fake.chain.2018 | 10.4242/fake.chain.2018 | `<null>` | 0 | 0 | Not Needed |
| `url` | no | https://doi.org/10.4242/fake.chain.2018 | https://doi.org/10.4242/fake.chain.2018 | `<null>` | 0 | 0 | Not Needed |

Warnings: `["auto_diff_only_fields=['journal']"]`

### TXT `txt:5`

Status: `status=critical_mismatch` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=1` | `recommended_candidate_rank=1`

Correction Summary: `targeted=4` | `fixed=4` | `correction_rate=1.0` | `targeted_source=manifest` | `status_score=0.0`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Halil Savuran, Murat Karakaya | Halil Savuran<br>Murat Karakaya | Halil Savuran, Murat Karakaya | 1 | 1 | Not Needed |
| `title` | yes | Efficient route planning for an unmanned air vehicle deployed on a stationary carrier | Efficient route planning for an unmanned air vehicle deployed on a moving carrier | Efficient route planning for an unmanned air vehicle deployed on a moving carrier | 0 | 1 | yes |
| `journal` | no | ". '' Soft Computing 20(7), 2905--2920 (2017), 20(7), 2905-2920 (2017) | ". '' Soft Computing 20(7), 2905--2920 (2017), 20(7), 2905-2920 (2017) | ". '' Soft Computing 20(7), 2905--2920 (2016), 20(7), 2905-2920 (2016) | 0 | 0 | Not Needed |
| `volume` | n/a | `<null>` | 20 | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | 7 | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | 2905-2920 | `<null>` | n/a | n/a | n/a |
| `year` | yes | 2017 | 2016 | 2016 | 0 | 1 | yes |
| `doi` | yes | 10.1007/s00500-015-1970-9 | 10.1007/s00500-015-1970-4 | 10.1007/s00500-015-1970-4 | 0 | 1 | yes |
| `url` | yes | https://doi.org/10.1007/s00500-015-1970-9 | https://doi.org/10.1007/s00500-015-1970-4 | https://doi.org/10.1007/s00500-015-1970-4 | 0 | 1 | yes |

Warnings: `["auto_diff_only_fields=['journal']"]`

### TXT `txt:6`

Status: `status=critical_mismatch` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=1` | `recommended_candidate_rank=1`

Correction Summary: `targeted=3` | `fixed=2` | `correction_rate=0.666667` | `targeted_source=manifest` | `status_score=0.0`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Murat Karakaya | Murat Karakaya | Murat Karakaya | 1 | 1 | Not Needed |
| `title` | yes | An Efficient Data Collection Heuristic for Wireless Sensor Networks with Limited Sensor Memory Capacity | MSCT: An Efficient Data Collection Heuristic for Wireless Sensor Networks with Limited Sensor Memory Capacity | MSCT: An Efficient Data Collection Heuristic for Wireless Sensor Networks with Limited Sensor Memory Capacity | 0 | 1 | yes |
| `journal` | yes | ". KSII Transactions on Internet and Information Systems, 9(4) (2015) | ". KSII Transactions on Internet and Information Systems, 9(4) (2015) | ". KSII Transactions on Internet and Information Systems, 9(9) (2015) | 0 | 0 | no |
| `volume` | n/a | `<null>` | 9 | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | 9 | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `year` | no | 2015 | 2015 | 2015 | 1 | 1 | Not Needed |
| `doi` | no | 10.3837/tiis.2015.09.007 | 10.3837/tiis.2015.09.007 | 10.3837/tiis.2015.09.007 | 1 | 1 | Not Needed |
| `url` | yes | https://example.com/fake/msct | https://doi.org/10.3837/tiis.2015.09.007 | https://doi.org/10.3837/tiis.2015.09.007 | 0 | 1 | yes |

### TXT `txt:7`

Status: `status=unresolved` | `selection_required=False` | `matched_by=title` | `selection_reason=none` | `selected_candidate_rank=None` | `recommended_candidate_rank=None`

Correction Summary: `targeted=0` | `fixed=0` | `correction_rate=1.0` | `targeted_source=manifest` | `status_score=0.6`

| Field | Targeted Wrong? | Benchmark Input | Corrected (Agent Patch) | Groundtruth | Benchmark vs GT | Corrected vs GT | Fixed? |
|---|---:|---|---|---|---:|---:|---:|
| `authors` | no | Murat Karakaya | Murat Karakaya | Murat Karakaya | 1 | 1 | Not Needed |
| `title` | no | Time-Sensitive Ant Colony Optimization to Schedule a Mobile Sink for Data Collection in Wireless Sensor Networks | Time-Sensitive Ant Colony Optimization to Schedule a Mobile Sink for Data Collection in Wireless Sensor Networks | Time-Sensitive Ant Colony Optimization to Schedule a Mobile Sink for Data Collection in Wireless Sensor Networks | 1 | 1 | Not Needed |
| `journal` | no | '' Ad Hoc 28(1--2), 65--92 (2015) | '' Ad Hoc 28(1--2), 65--92 (2015) | '' Ad Hoc 28(1--2), 65--82 (2015) | 0 | 0 | Not Needed |
| `volume` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `issue` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `pages` | n/a | `<null>` | `<null>` | `<null>` | n/a | n/a | n/a |
| `year` | no | 2015 | 2015 | 2015 | 1 | 1 | Not Needed |
| `doi` | no | 10.5555/ahsn.2015.028 | 10.5555/ahsn.2015.028 | `<null>` | 0 | 0 | Not Needed |
| `url` | no | https://doi.org/10.5555/ahsn.2015.028 | https://doi.org/10.5555/ahsn.2015.028 | `<null>` | 0 | 0 | Not Needed |

Warnings: `["auto_diff_only_fields=['journal']"]`
