# Kata 2 — Pagination iterators

Implement `iterate_offset` and `iterate_cursor` as async generators that call the fetch callback until exhausted.

<details>
<summary>Model answer</summary>

Offset: loop `offset=0`, fetch until `offset >= total` or empty items.
Cursor: loop with `cursor=None`, then next cursor until `None`.

</details>
