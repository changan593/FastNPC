# -*- coding: utf-8 -*-
from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("fastnpc.api.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()


