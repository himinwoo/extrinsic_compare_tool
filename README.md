# Extrinsic Compare Tool

Radar-LiDAR extrinsic 후보를 빠르게 만들고, 같은 프레임 샘플에 반복 적용해서 CloudCompare로 비교하기 위한 작은 CLI입니다.

## 목표

- 데이터셋마다 다른 Radar/LiDAR 폴더와 sync 파일을 인자로 받기
- 4x4 extrinsic 후보를 yaw/pitch/roll/translation sweep으로 생성하기
- 후보별로 동일한 프레임 범위를 변환하여 색상 PCD 출력하기
- 필요할 때 CloudCompare를 바로 실행하기

## 설치

```bash
cd /home/himinwoo/calib_ws/extrinsic_compare_tool
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install -e .
```

이미 `.venv`를 만든 뒤라면 다음을 확인하세요.

```bash
python -c "import numpy; print(numpy.__version__)"
```

`numpy`가 없다고 나오면 venv를 `--system-site-packages` 옵션으로 다시 만들거나, 네트워크가 가능한 환경에서 `pip install numpy`를 먼저 실행하면 됩니다.

## 빠른 사용

변환 후보 생성:

```bash
ecmp variants \
  --base examples/radar_to_lidar_4x4_ascii.txt \
  --out-dir outputs/variants \
  --yaw=-2,-1,0,1,2 \
  --pitch=0 \
  --roll=0
```

단일 extrinsic 시각화 PCD 생성:

```bash
ecmp view \
  --data-dir /media/himinwoo/Samsung_T5/LG_IT/pcd \
  --sync-file radar_Continental_lidar_Hesai.txt \
  --radar-dir radar_Continental \
  --lidar-dir lidar_Hesai \
  --transform-file examples/radar_to_lidar_4x4_ascii.txt \
  --start-idx 0 \
  --num-frames 10 \
  --step 50 \
  --no-launch \
  --output-dir outputs/single
```

후보 폴더 전체 비교용 출력 생성:

```bash
ecmp compare \
  --data-dir /media/himinwoo/Samsung_T5/LG_IT/pcd \
  --sync-file radar_Continental_lidar_Hesai.txt \
  --radar-dir radar_Continental \
  --lidar-dir lidar_Hesai \
  --transforms-dir outputs/variants \
  --start-idx 0 \
  --num-frames 10 \
  --step 50 \
  --merge \
  --output-dir outputs/compare
```

CloudCompare까지 바로 열고 싶으면 `view`에서 `--no-launch`를 빼면 됩니다. `compare`는 후보가 많아질 수 있어서 기본적으로 파일 생성만 합니다.

## 권장 작업 흐름

1. 기준 extrinsic을 `examples/` 또는 실험별 폴더에 보관합니다.
2. `ecmp variants`로 후보를 생성합니다.
3. `ecmp compare`로 후보별 동일 프레임 출력물을 만듭니다.
4. CloudCompare에서 후보별 `merged_radar.pcd`, `merged_lidar.pcd`를 열어 정렬 상태를 비교합니다.
5. 가장 나은 후보를 기준으로 더 좁은 sweep을 반복합니다.
