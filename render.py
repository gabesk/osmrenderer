import xml.etree.ElementTree as etree
import xml.parsers.expat
from PIL import Image
from PIL import ImageDraw

nodes = {}
ways = {}

class Map(object):
    '''Parses a file containing OSM XML data
    (http://wiki.openstreetmap.org/wiki/OSM_XML) into nodes and ways dicts keyed
    by node and way id attribute. Use expat parser instead of a DOM-based one
    to allow parsing larger maps without running out of memory.'''
    def __init__(self, map_filename):
        self.nodes = {}
        self.ways = {}
        self._nds = []
        self._way = None
        self._lon_min, self._lon_max, self._lat_min, self._lat_max = None, None, None, None

        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = lambda name, attrs: Map.start_element(self, name, attrs)
        p.EndElementHandler = lambda name: Map.end_element(self, name)
        p.CharacterDataHandler = lambda data: Map.char_data(self, data)

        print 'Opening ' + map_filename
        map_filehandle = open(map_filename, 'rb')
        print 'done'

        print 'Parsing'
        p.ParseFile(map_filehandle)
        print 'done'

    def start_element(self, name, attrs):
        if name == 'node':
            if u'id' in attrs:
                self.nodes[attrs[u'id']] = (attrs[u'uid'], float(attrs[u'lat']), float(attrs[u'lon']))
        elif name == 'way':
            self._nds = []
            self._way = {}
            self._way[u'id'] = attrs[u'id']
            self._way[u'uid'] = attrs[u'uid']

        if self._way:
            if name == 'nd':
                self._nds.append(attrs[u'ref'])

    def end_element(self, name):
        if name == 'way':
            self._way[u'nds'] = self._nds
            self.ways[self._way[u'id']] = self._way
            self._way = None

    def char_data(self, data):
        pass

    def bounds(self):
        # Use cached results if already available
        if self._lon_min:
            return self._lon_min, self._lon_max, self._lat_min, self._lat_max

        print 'Finding bounding box'
        self._lon_min, self._lon_max, self._lat_min, self._lat_max = 180.0, -180.0, 180.0, -180.0
        for id, node in self.nodes.iteritems():
            uid, lat, lon = node
            if lon < self._lon_min:
                self._lon_min = lon
            elif lon > self._lon_max:
                self._lon_max = lon

            if lat < self._lat_min:
                self._lat_min = lat
            elif lat > self._lat_max:
                self._lat_max = lat

        print self._lon_min, self._lon_max, self._lon_max - self._lon_min
        print self._lat_min, self._lat_max, self._lat_max - self._lat_min
        print 'done'
        return self._lon_min, self._lon_max, self._lat_min, self._lat_max

class Renderer(object):
    WIDTH = 2000
    HEIGHT = 2000

    def __init__(self, map):
        self.nodes = map.nodes
        self.ways = map.ways
        self._lon_min, self._lon_max, self._lat_min, self._lat_max = map.bounds()        

    def transform_to_screen_px(self, lon, lat):
        lon_norm = (lon - self._lon_min) / (self._lon_max - self._lon_min)
        lat_norm = (lat - self._lat_min) / (self._lat_max - self._lat_min)
        lon_px = lon_norm * Renderer.WIDTH
        lat_px = lat_norm * Renderer.HEIGHT
        return int(lon_px), Renderer.HEIGHT-int(lat_px)

    def create_png(self, filename):
        im = Image.new("RGB", (Renderer.WIDTH+1, Renderer.HEIGHT+1), "white")
        print 'Printing lines'
        draw = ImageDraw.Draw(im)
        for id, way in self.ways.iteritems():
            last_x, last_y = None, None
            for nd in way[u'nds']:
                node = self.nodes[nd]
                uid, lat, lon = node
                x, y = self.transform_to_screen_px(lon, lat)
                if last_x:
                    draw.line(((last_x, last_y), (x, y)), fill=0)
                last_x, last_y = x, y
        print 'done'
        print 'Printing dots'
        for id, node in self.nodes.iteritems():
            uid, lat, lon = node
            x, y = self.transform_to_screen_px(lon, lat)
            im.putpixel((x,y), 0x0000FF) # red color
        print 'done'

        im.save(filename)

map_obj = Map('map.osm')
rend_obj = Renderer(map_obj)
rend_obj.create_png('test.png')