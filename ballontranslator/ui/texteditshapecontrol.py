import math
import numpy as np

from qtpy.QtWidgets import QGraphicsPixmapItem, QGraphicsItem, QWidget, QGraphicsSceneHoverEvent, QLabel, QStyleOptionGraphicsItem, QGraphicsSceneMouseEvent, QGraphicsRectItem
from qtpy.QtCore import Qt, QRect, QRectF, QPointF, QPoint
from qtpy.QtGui import QPainter, QPen, QColor
from utils.imgproc_utils import xywh2xyxypoly, rotate_polygons
from typing import List, Union, Tuple

from .cursor import rotateCursorList, resizeCursorList
from .textitem import TextBlkItem

class ControlBlockItem(QGraphicsRectItem):
    DRAG_NONE = 0
    DRAG_RESHAPE = 1
    DRAG_ROTATE = 2
    CURSOR_IDX = -1
    def __init__(self, parent, idx: int, edge_len: float):
        super().__init__(parent)
        # self.setParentItem(parent)
        self.idx = idx
        self.ctrl: TextBlkShapeControl = parent
        self.edge_len = edge_len
        self.visible_len = self.edge_len // 2
        self.pen_width = 2
        self.setPen(QPen(QColor(75, 75, 75), self.pen_width, Qt.PenStyle.SolidLine, Qt.SquareCap))
        offset = self.edge_len // 4 + self.pen_width / 2
        self.visible_rect = QRectF(offset, offset, self.visible_len, self.visible_len)
        self.drag_mode = self.DRAG_NONE
        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setRect(0, 0, self.edge_len, self.edge_len)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget) -> None:
        rect = QRectF(self.visible_rect)
        rect.setTopLeft(self.boundingRect().topLeft()+rect.topLeft())
        painter.setPen(QPen(QColor(75, 75, 75), self.pen_width, Qt.PenStyle.SolidLine, Qt.SquareCap))
        painter.fillRect(rect, QColor(200, 200, 200, 125))
        painter.drawRect(rect)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:        
        return super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.drag_mode = self.DRAG_NONE
        self.CURSOR_IDX = -1
        return super().hoverLeaveEvent(event)

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        angle = self.ctrl.rotation() + 45 * self.idx
        idx = self.get_angle_idx(angle)
        if self.visible_rect.contains(event.pos()):
            self.setCursor(resizeCursorList[idx % 4])
        else:
            self.setCursor(rotateCursorList[idx])
        self.CURSOR_IDX = idx
        return super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.ctrl.ctrlblockPressed()
        if event.button() == Qt.MouseButton.LeftButton:
            self.ctrl.reshaping = True
            if self.visible_rect.contains(event.pos()):
                self.drag_mode = self.DRAG_RESHAPE
                self.ctrl.blk_item.startReshape()
            else:
                self.drag_mode = self.DRAG_ROTATE
                preview = self.ctrl.previewPixmap
                preview.setPixmap(self.ctrl.blk_item.toPixmap())
                preview.setOpacity(0.7)
                preview.setScale(self.ctrl.blk_item.scale())
                preview.setVisible(True)

                rotate_vec = event.scenePos() - self.ctrl.pos() - self.ctrl.boundingRect().center()
                self.updateAngleLabelPos()
                rotation = np.rad2deg(math.atan2(rotate_vec.y(), rotate_vec.x()))
                self.rotate_start = - rotation + self.ctrl.rotation() 
        event.accept()

    def updateAngleLabelPos(self):
        angleLabel = self.ctrl.angleLabel
        sp = self.scenePos()
        gv = angleLabel.parent()
        pos = gv.mapFromScene(sp.toPoint())
        x = max(min(pos.x(), gv.width() - angleLabel.width()), 0)
        y = max(min(pos.y(), gv.height() - angleLabel.height()), 0)
        angleLabel.move(QPoint(x, y))
        angleLabel.setText("{:.1f}°".format(self.ctrl.rotation()))
        if not angleLabel.isVisible():
            angleLabel.setVisible(True)
            angleLabel.raise_()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        blk_item = self.ctrl.blk_item
        if self.drag_mode == self.DRAG_RESHAPE:
            
            block_group = self.ctrl.ctrlblock_group
            old_pos = QPointF(block_group[0].scenePos())
            super().mouseMoveEvent(event)
            
            crect = self.ctrl.rect()
            pos_x, pos_y = 0, 0
            opposite_block = block_group[(self.idx + 4) %8 ]
            oppo_pos = opposite_block.pos()
            if self.idx % 2 == 0:
                if self.idx == 0:
                    pos_x = min(self.pos().x(), oppo_pos.x())
                    pos_y = min(self.pos().y(), oppo_pos.y())
                    crect.setX(pos_x+self.visible_len)
                    crect.setY(pos_y+self.visible_len)
                elif self.idx == 2:
                    pos_x = max(self.pos().x(), oppo_pos.x())
                    pos_y = min(self.pos().y(), oppo_pos.y())
                    crect.setWidth(pos_x-oppo_pos.x())
                    crect.setY(pos_y+self.visible_len)
                elif self.idx == 4:
                    pos_x = max(self.pos().x(), oppo_pos.x())
                    pos_y = max(self.pos().y(), oppo_pos.y())
                    crect.setWidth(pos_x-oppo_pos.x())
                    crect.setHeight(pos_y-oppo_pos.y())
                else:   # idx == 6
                    pos_x = min(self.pos().x(), oppo_pos.x())
                    pos_y = max(self.pos().y(), oppo_pos.y())
                    crect.setX(pos_x+self.visible_len)
                    crect.setHeight(pos_y-oppo_pos.y())
            else:
                if self.idx == 1:
                    pos_y = min(self.pos().y(), oppo_pos.y())
                    crect.setY(pos_y+self.visible_len)
                elif self.idx == 3:
                    pos_x = max(self.pos().x(), oppo_pos.x())
                    crect.setWidth(pos_x-oppo_pos.x())
                elif self.idx == 5:
                    pos_y = max(self.pos().y(), oppo_pos.y())
                    crect.setHeight(pos_y-oppo_pos.y())
                else:   # idx == 7
                    pos_x = min(self.pos().x(), oppo_pos.x())
                    crect.setX(pos_x+self.visible_len)
            
            self.ctrl.setRect(crect)
            rect = QRectF()
            rect.setTopLeft(blk_item.pos()+block_group[0].scenePos()-old_pos)
            rect.setBottomRight(crect.bottomRight()-crect.topLeft()+rect.topLeft())
            rect.setHeight(rect.height()/blk_item.scale())
            rect.setWidth(rect.width()/blk_item.scale())
            new_center = self.ctrl.sceneBoundingRect().center()
            rect.setX(new_center.x()-rect.width()/2)
            rect.setY(new_center.y()-rect.height()/2)
            blk_item.setRect(rect)

        elif self.drag_mode == self.DRAG_ROTATE:   # rotating
            rotate_vec = event.scenePos() - self.ctrl.pos() - self.ctrl.boundingRect().center()
            rotation = np.rad2deg(math.atan2(rotate_vec.y(), rotate_vec.x()))
            self.ctrl.setAngle(rotation+self.rotate_start)
            angle = self.ctrl.rotation() + 45 * self.idx
            idx = self.get_angle_idx(angle)
            if self.CURSOR_IDX != idx:
                self.setCursor(rotateCursorList[idx])
                self.CURSOR_IDX = idx
            self.updateAngleLabelPos()

    def get_angle_idx(self, angle) -> int:
        idx = int((angle + 22.5) % 360 / 45)
        return idx
    
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.ctrl.reshaping = False
            if self.drag_mode == self.DRAG_RESHAPE:
                self.ctrl.blk_item.endReshape()
            if self.drag_mode == self.DRAG_ROTATE:
                self.ctrl.blk_item.rotated.emit(self.ctrl.rotation())
            self.drag_mode = self.DRAG_NONE
            
            self.ctrl.previewPixmap.setVisible(False)
            self.ctrl.angleLabel.setVisible(False)
            self.ctrl.blk_item.update()
            self.ctrl.updateBoundingRect()
            return super().mouseReleaseEvent(event)


class TextBlkShapeControl(QGraphicsRectItem):
    blk_item : TextBlkItem = None 
    cb_edge_len : float = 40
    ctrl_block: ControlBlockItem = None
    reshaping: bool = False
    
    def __init__(self, parent) -> None:
        super().__init__()
        self.gv = parent
        self.ctrlblock_group = [
            ControlBlockItem(self, 0, self.cb_edge_len),
            ControlBlockItem(self, 1, self.cb_edge_len),
            ControlBlockItem(self, 2, self.cb_edge_len),
            ControlBlockItem(self, 3, self.cb_edge_len),
            ControlBlockItem(self, 4, self.cb_edge_len),
            ControlBlockItem(self, 5, self.cb_edge_len),
            ControlBlockItem(self, 6, self.cb_edge_len),
            ControlBlockItem(self, 7, self.cb_edge_len),
        ]
        
        self.previewPixmap = QGraphicsPixmapItem(self)
        self.previewPixmap.setVisible(False)
        pen = QPen(QColor(69, 71, 87), 2, Qt.PenStyle.SolidLine)
        pen.setDashPattern([7, 14])
        self.setPen(pen)
        self.setVisible(False)
        self.setZValue(1)

        self.angleLabel = QLabel(parent)
        self.angleLabel.setText("{:.1f}°".format(self.rotation()))
        self.angleLabel.setObjectName("angleLabel")
        self.angleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.angleLabel.setHidden(True)

        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def setBlkItem(self, blk_item: TextBlkItem):
        if self.blk_item == blk_item and self.isVisible():
            return
        if self.blk_item is not None:
            self.blk_item.under_ctrl = False
            self.blk_item.setFocus(Qt.FocusReason.NoFocusReason)
            self.blk_item.update()
            
        self.blk_item = blk_item
        if blk_item is None:
            self.hide()
            return
        blk_item.under_ctrl = True
        blk_item.update()
        self.updateBoundingRect()
        self.show()

    def updateBoundingRect(self):
        if self.blk_item is None:
            return
        br = self.blk_item.boundingRect()
        center = br.center()
        scale = self.blk_item.scale()
        ds = 1 - scale
        br = [0, 0, br.width()*scale, br.height()*scale]
        self.blk_item.setCenterTransform()
        self.setTransformOriginPoint(self.blk_item.transformOriginPoint())
        self.setRect(*br)
        pos = self.blk_item.pos()
        self.setPos(pos.x()+ds*center.x(), pos.y()+ds*center.y())
        self.setAngle(self.blk_item.angle)

    def setRect(self, *args): 
        super().setRect(*args)
        self.updateControlBlocks()

    def updateControlBlocks(self):
        b_rect = self.rect()
        b_rect = [b_rect.x(), b_rect.y(), b_rect.width(), b_rect.height()]
        corner_pnts = xywh2xyxypoly(np.array([b_rect])).reshape(-1, 2)
        edge_pnts = (corner_pnts[[1, 2, 3, 0]] + corner_pnts) / 2
        pnts = [edge_pnts, corner_pnts]
        offset = -0.5 * self.cb_edge_len
        for ii, ctrlblock in enumerate(self.ctrlblock_group):
            is_corner = not ii % 2
            idx = ii // 2
            pos = pnts[is_corner][idx] + offset
            ctrlblock.setPos(pos[0], pos[1])

    def setAngle(self, angle: int) -> None:
        center = self.boundingRect().center()
        self.setTransformOriginPoint(center)
        self.setRotation(angle)

    def ctrlblockPressed(self):
        self.scene().clearSelection()

    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget = ...) -> None:
        painter.setCompositionMode(QPainter.RasterOp_NotDestination)
        super().paint(painter, option, widget)

    def hideControls(self):
        for ctrl in self.ctrlblock_group:
            ctrl.hide()

    def showControls(self):
        for ctrl in self.ctrlblock_group:
            ctrl.show()