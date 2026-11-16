import java.math.BigInteger;
import java.security.MessageDigest;
import java.security.SecureRandom;

public final class Ecdsa {
    private static final SecureRandom RANDOM = new SecureRandom();

    private static final Curve CURVE = new Curve(
            hex("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F"),
            hex("0"),
            hex("7"),
            new Point(
                    hex("79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798"),
                    hex("483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8")),
            hex("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141"));

    private static final String MESSAGE_HEX = "48656c6c6f";
    private static final String EXPECTED_SHA256_HEX =
            "185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969";

    private Ecdsa() { }

    public static void main(String[] args) throws Exception {
        byte[] message = decodeHex(MESSAGE_HEX);
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(message);
        String digestHex = toHex(digest);
        if (!digestHex.equals(EXPECTED_SHA256_HEX)) {
            throw new IllegalStateException("SHA-256 test vector mismatch");
        }
        BigInteger e = new BigInteger(1, digest).mod(CURVE.q);

        System.out.println("Curve: secp256k1");
        System.out.println("Message (hex): " + MESSAGE_HEX);
        System.out.println("SHA-256 (hex): " + digestHex);

        BigInteger alicePrivate = randomScalar(CURVE.q);
        BigInteger bobPrivate = randomScalar(CURVE.q);
        Point alicePublic = CURVE.multiply(alicePrivate, CURVE.g);
        Point bobPublic = CURVE.multiply(bobPrivate, CURVE.g);
        Point aliceShared = CURVE.multiply(alicePrivate, bobPublic);
        Point bobShared = CURVE.multiply(bobPrivate, alicePublic);
        if (aliceShared.infinity || bobShared.infinity || !aliceShared.x.equals(bobShared.x)) {
            throw new IllegalStateException("ECDH shared secret mismatch");
        }
        System.out.println("Alice public Qx: " + toFixedHex(alicePublic.x, 32));
        System.out.println("Alice public Qy: " + toFixedHex(alicePublic.y, 32));
        System.out.println("Bob public Qx:   " + toFixedHex(bobPublic.x, 32));
        System.out.println("Bob public Qy:   " + toFixedHex(bobPublic.y, 32));
        System.out.println("ECDH shared x:   " + toFixedHex(aliceShared.x, 32));
        System.out.println("ECDH equal:      true");

        BigInteger privateKey = randomScalar(CURVE.q);
        Point publicKey = CURVE.multiply(privateKey, CURVE.g);
        Signature signature = sign(e, privateKey);
        boolean valid = verify(e, signature, publicKey);
        if (!valid) {
            throw new IllegalStateException("Signature verification failed");
        }

        System.out.println("Public key Qx:   " + toFixedHex(publicKey.x, 32));
        System.out.println("Public key Qy:   " + toFixedHex(publicKey.y, 32));
        System.out.println("Signature r:     " + toFixedHex(signature.r, 32));
        System.out.println("Signature s:     " + toFixedHex(signature.s, 32));
        System.out.println("ECDSA valid:     " + valid);

        BigInteger tamperedS = signature.s.xor(BigInteger.ONE);
        if (tamperedS.signum() == 0 || tamperedS.compareTo(CURVE.q) >= 0) {
            tamperedS = signature.s.add(BigInteger.ONE).mod(CURVE.q);
        }
        boolean tamperedValid = verify(e, new Signature(signature.r, tamperedS), publicKey);
        System.out.println("Tampered s:      " + toFixedHex(tamperedS, 32));
        System.out.println("Tampered valid:  " + tamperedValid);
        if (tamperedValid) {
            throw new IllegalStateException("Modified signature was accepted");
        }
    }

    private static Signature sign(BigInteger e, BigInteger privateKey) {
        if (privateKey.signum() <= 0 || privateKey.compareTo(CURVE.q) >= 0) {
            throw new IllegalArgumentException("Private key is out of range");
        }
        while (true) {
            BigInteger k = randomScalar(CURVE.q);
            Point c = CURVE.multiply(k, CURVE.g);
            BigInteger r = c.x.mod(CURVE.q);
            if (r.signum() == 0) continue;
            BigInteger s = inverseFermat(k, CURVE.q)
                    .multiply(e.add(r.multiply(privateKey))).mod(CURVE.q);
            if (s.signum() != 0) return new Signature(r, s);
        }
    }

    private static boolean verify(BigInteger e, Signature signature, Point publicKey) {
        BigInteger r = signature.r;
        BigInteger s = signature.s;
        if (r.signum() <= 0 || r.compareTo(CURVE.q) >= 0
                || s.signum() <= 0 || s.compareTo(CURVE.q) >= 0
                || !CURVE.isOnCurve(publicKey) || publicKey.infinity) {
            return false;
        }
        BigInteger w;
        try {
            w = inverseFermat(s, CURVE.q);
        } catch (ArithmeticException ex) {
            return false;
        }
        BigInteger u1 = e.multiply(w).mod(CURVE.q);
        BigInteger u2 = r.multiply(w).mod(CURVE.q);
        Point c = CURVE.add(CURVE.multiply(u1, CURVE.g), CURVE.multiply(u2, publicKey));
        return !c.infinity && c.x.mod(CURVE.q).equals(r);
    }

    private static BigInteger inverseFermat(BigInteger a, BigInteger m) {
        BigInteger base = a.mod(m);
        BigInteger exponent = m.subtract(BigInteger.valueOf(2));
        BigInteger result = BigInteger.ONE;
        for (int i = exponent.bitLength() - 1; i >= 0; --i) {
            result = result.multiply(result).mod(m);
            if (exponent.testBit(i)) result = result.multiply(base).mod(m);
        }
        return result;
    }

    private static BigInteger randomScalar(BigInteger upperExclusive) {
        BigInteger value;
        do {
            value = new BigInteger(upperExclusive.bitLength(), RANDOM);
        } while (value.signum() == 0 || value.compareTo(upperExclusive) >= 0);
        return value;
    }

    private static final class Curve {
        final BigInteger p;
        final BigInteger a;
        final BigInteger b;
        final Point g;
        final BigInteger q;

        Curve(BigInteger p, BigInteger a, BigInteger b, Point g, BigInteger q) {
            this.p = p;
            this.a = a;
            this.b = b;
            this.g = g;
            this.q = q;
            if (!isOnCurve(g)) throw new IllegalArgumentException("Invalid base point");
        }

        boolean isOnCurve(Point point) {
            if (point == null) return false;
            if (point.infinity) return true;
            if (point.x.signum() < 0 || point.x.compareTo(p) >= 0
                    || point.y.signum() < 0 || point.y.compareTo(p) >= 0) return false;
            BigInteger left = point.y.multiply(point.y).mod(p);
            BigInteger right = point.x.multiply(point.x).multiply(point.x)
                    .add(a.multiply(point.x)).add(b).mod(p);
            return left.equals(right);
        }

        Point add(Point p1, Point p2) {
            if (p1.infinity) return p2;
            if (p2.infinity) return p1;
            if (p1.x.equals(p2.x)) {
                if (p1.y.add(p2.y).mod(p).signum() == 0) return Point.INFINITY;
                return twice(p1);
            }
            BigInteger slope = p2.y.subtract(p1.y).mod(p)
                    .multiply(inverseFermat(p2.x.subtract(p1.x), p)).mod(p);
            BigInteger x3 = slope.multiply(slope).subtract(p1.x).subtract(p2.x).mod(p);
            BigInteger y3 = slope.multiply(p1.x.subtract(x3)).subtract(p1.y).mod(p);
            return new Point(x3, y3);
        }

        Point twice(Point point) {
            if (point.infinity || point.y.signum() == 0) return Point.INFINITY;
            BigInteger numerator = point.x.multiply(point.x).multiply(BigInteger.valueOf(3)).add(a);
            BigInteger denominator = point.y.shiftLeft(1);
            BigInteger slope = numerator.mod(p).multiply(inverseFermat(denominator, p)).mod(p);
            BigInteger x3 = slope.multiply(slope).subtract(point.x.shiftLeft(1)).mod(p);
            BigInteger y3 = slope.multiply(point.x.subtract(x3)).subtract(point.y).mod(p);
            return new Point(x3, y3);
        }

        Point multiply(BigInteger scalar, Point point) {
            if (scalar.signum() < 0) throw new IllegalArgumentException("Negative scalar");
            Point result = Point.INFINITY;
            for (int i = q.bitLength() - 1; i >= 0; --i) {
                result = twice(result);
                if (scalar.testBit(i)) result = add(result, point);
            }
            return result;
        }
    }

    private static final class Point {
        static final Point INFINITY = new Point();
        final BigInteger x;
        final BigInteger y;
        final boolean infinity;

        private Point() {
            this.x = BigInteger.ZERO;
            this.y = BigInteger.ZERO;
            this.infinity = true;
        }

        Point(BigInteger x, BigInteger y) {
            this.x = x;
            this.y = y;
            this.infinity = false;
        }
    }

    private static final class Signature {
        final BigInteger r;
        final BigInteger s;
        Signature(BigInteger r, BigInteger s) {
            this.r = r;
            this.s = s;
        }
    }

    private static BigInteger hex(String value) {
        return new BigInteger(value, 16);
    }

    private static byte[] decodeHex(String value) {
        if ((value.length() & 1) != 0) throw new IllegalArgumentException("Odd-length Hex string");
        byte[] result = new byte[value.length() / 2];
        for (int i = 0; i < result.length; ++i) {
            int high = Character.digit(value.charAt(i * 2), 16);
            int low = Character.digit(value.charAt(i * 2 + 1), 16);
            if (high < 0 || low < 0) throw new IllegalArgumentException("Invalid Hex string");
            result[i] = (byte) ((high << 4) | low);
        }
        return result;
    }

    private static String toHex(byte[] value) {
        StringBuilder out = new StringBuilder(value.length * 2);
        for (byte b : value) out.append(String.format("%02x", b & 0xff));
        return out.toString();
    }

    private static String toFixedHex(BigInteger value, int byteLength) {
        String raw = value.toString(16);
        int expected = byteLength * 2;
        if (raw.length() > expected) throw new IllegalArgumentException("Value does not fit");
        StringBuilder out = new StringBuilder(expected);
        for (int i = raw.length(); i < expected; ++i) out.append('0');
        return out.append(raw).toString();
    }
}